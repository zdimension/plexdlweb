from datetime import timedelta

import asyncio
import humanize
from fastapi import Request
from fastapi.responses import RedirectResponse, FileResponse
from nicegui import ui, app
from plexapi.collection import *
from plexapi.video import *
from plexapi.media import MediaPart, Media

from config import config
from login import check_login, logout
from plex import get_server, get_self
from locales import _

from common import io_bound


@app.middleware("http")
async def check_auth(request: Request, call_next):
    # https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py
    if not await check_login():
        if not request.url.path.startswith("/_nicegui") and request.url.path != "/login":
            app.storage.user['referrer_path'] = request.url.path
            return RedirectResponse('/login')
    return await call_next(request)


# todo: find a way
# class CustomGZipMiddleware(GZipMiddleware):
#     def __init__(
#         self, *args, **kwargs
#     ) -> None:
#         super().__init__(*args, **kwargs)

#     async def __call__(self, scope, receive, send) -> None:
#         if scope["type"] == "http":
#             headers = Headers(scope=scope)
#             if "gzip" in headers.get("Accept-Encoding", ""):
#                 responder = GZipResponder(
#                     self.app, self.minimum_size, compresslevel=self.compresslevel
#                 )
#                 await responder(scope, receive, send)
#                 return
#         await self.app(scope, receive, send)

del app.user_middleware[-1]  # gzip removes content-length


async def header():
    """
    Displays thecommon page header
    """
    user = await get_self()

    with ui.row():
        ui.button(_("home"), on_click=lambda: ui.open("/"))
        ui.button(_("logout"), on_click=logout)
        ui.label(_("user", user=user.email))


@app.get("/download/{media}/{index}")
async def download(media: int, index: int):
    """
    Downloads the specified media part from Plex
    """
    part = (await get_server()).fetchItem(media).media[index].parts[0]  # is there ever more than one part per media?
    filename = os.path.basename(part.file)
    return FileResponse(part.file, filename=filename, stat_result=os.stat(part.file))


@ui.page("/", title="PlexDLWeb")
async def index():
    ui.add_head_html("""
        <link rel="manifest" href="/plexdlweb.webmanifest">
        <style>
            /* for search results */
            .cursor-pointer-rec, .cursor-pointer-rec * {
                cursor: pointer;
            }
        </style>
    """)

    ui.add_body_html("""
        <script>
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js');
            }
        </script>
    """)

    def fake_button_group():
        return ui.element("div").classes(add="q-btn-group row flex-nowrap")

    def fake_button(text):
        with ui.element("div").classes(add="q-btn q-btn-item no-outline") as e:
            with ui.element("span").classes(add="text-left items-center justify-center col row"):
                ui.html(text)
            return e

    def fake_button_label(text):
        return ui.label(text).classes(add="m-3 q-btn q-btn--flat p-0").style("min-height: 0")
    
    def duration_to_string(ms: int):
        dur = timedelta(milliseconds=ms)
        if dur > timedelta(hours=1):
            return f"{dur.seconds // 3600}h{(dur.seconds // 60) % 60}m"
        elif dur > timedelta(minutes=5):
            return f"{dur.seconds // 60}m"
        else:
            return f"{dur.seconds // 60}m{dur.seconds % 60}s"

    def merge(query, new):
        """
        Merge the previous query history with the new one
        Example: merge([A,B], [C,D]) == [A,B,C,D]
        Handles overlaps: merge([A,B,C], [B,D,E]) == [A,B,D,E]
        """
        try:
            idx = query.index(new[0])
            return query[:idx] + new
        except ValueError:
            return [*query, *new]

    @ui.refreshable
    def result_list(query, results):
        def refresh(query2, results2):
            # don't refresh if the parameters haven't changed
            if (query2, results2) == (query, results):
                return
            result_list.refresh(query2, results2)

        if not query:
            return
        if not results:
            ui.label(_("no_results"))
            return
        kinds = {
            Movie: (
                _("movie"),
                "bg-green-300",
                lambda m: (f"<span style='font-size: 70%'>{m.editionTitle}</span><br>" if m.editionTitle else "") + m.title,
                lambda m: print(list(m.iterParts()))
            ),
            Show: (
                _("show"),
                "bg-yellow-300",
                lambda s: s.title,
                lambda s: refresh([*query, s], s.seasons())
            ),
            Season: (
                _("season"),
                "bg-red-300",
                lambda s: f"{s.parentTitle} - {s.title}",
                lambda s: refresh([*query, s], s.episodes())
            ),
            Episode: (
                _("episode"),
                "bg-teal-300",
                lambda
                    e: f"<span style='font-size: 70%'>{e.grandparentTitle} - {e.parentTitle} - Épisode {e.index}</span><br>{e.title}",
                lambda e: refresh(merge(query, [e.show(), sea := e.season()]), sea.episodes())
            ),
            Collection: (
                _("collection"),
                "bg-violet-300",
                lambda c: c.title,
                lambda c: refresh([*query, c], c.items())
            ),
            str: (
                _("search_noun"),
                "bg-blue-300",
                lambda s: s,
                lambda s: do_search(s, True)
            )
        }
        result_as_list = app.storage.user.get("result_as_list", False)
        with ui.row():
            def format_change(e):
                app.storage.user['result_as_list'] = e.value
                result_list.refresh(query, results)

            ui.label(_("display"))
            ui.toggle({False: _("grid"), True: _("list")}, value=result_as_list, on_change=format_change)

        with ui.row():
            ui.label(_("history"))

            def display_crumb(i, part):
                kind, color, namer, clicked = kinds[type(part)]

                async def handler():
                    del query[i:]
                    await clicked(part)

                with fake_button_group().on("click", handler).classes(add="cursor-pointer-rec"):
                    fake_button(kind).classes(add=color)
                    fake_button(namer(part))

            for i, part in enumerate(query):
                display_crumb(i, part)
                
        with ui.column() if result_as_list else ui.grid(columns=3):
            def display_result(r):
                opts = kinds.get(type(r), None)
                if opts is None:
                    return
                kind, color, namer, clicked = opts

                def dl_button():
                    if isinstance(r, Playable):
                        if len(r.media) > 1:
                            def handler():
                                def part_line(i, media: Media):
                                    part = media.parts[0]
                                    fake_button_label(duration_to_string(part.duration)).style("text-transform: none").classes(add="text-right")
                                    fake_button_label(f"{media.width}x{media.height}").style("text-transform: none")
                                    fake_button_label(humanize.naturalsize(part.size)).classes(add="text-right")
                                    ui.button(icon="download").props("flat").on("click.stop", lambda: ui.download(f"/download/{r.ratingKey}/{i}")).classes(add="px-3")
                                with ui.dialog() as dialog, ui.card():
                                    with ui.grid(columns=4):
                                        for i, media in enumerate(r.media):
                                            part_line(i, media)
                                dialog.open()
                        else:
                            def handler():
                                ui.download(f"/download/{r.ratingKey}/0")
                        part = r.media[0].parts[0]
                        fake_button_label(duration_to_string(part.duration)).classes(add="ml-auto self-center").style(
                            "text-transform: none; font-size: 90%")
                        fake_button_label(humanize.naturalsize(part.size)).classes(add="mx-0 self-center").style(
                            "font-size: 90%")
                        ui.button(icon="download").props("flat").on("click.stop", handler).classes(add="px-3")

                if result_as_list:
                    with fake_button_group().on("click", lambda: clicked(r)).classes(add="w-full cursor-pointer-rec"):
                        fake_button(kind).classes(add=color)
                        fake_button(namer(r))
                        dl_button()
                else:
                    with ui.card().tight().on("click", lambda: clicked(r)).classes(add="cursor-pointer-rec"):
                        with ui.card_section().classes(add=color).classes(add="p-0 row"):
                            fake_button_label(kind)
                            dl_button()
                        ui.image("/plex" + r.thumb)
                        with ui.card_section():
                            ui.html("<span style='font-size: 120%'>" + namer(r) + "</span>")

            for r in results:
                display_result(r)

    last_search = None

    server = await get_server()

    async def do_search(query, force=False):
        nonlocal last_search
        previous, last_search = last_search, query
        if not force and query == previous or len(query) < 3:
            return

        loading.set_visibility(True)
        results = await io_bound(server.search, query)
        async def all_editions(x):
            if isinstance(x, Movie):
                return [x, *(await io_bound(x.editions))]
            return [x]
        result_list.refresh([query], [item for editions in (await asyncio.gather(*[all_editions(res) for res in results])) for item in editions])
        loading.set_visibility(False)

    debounce = None

    def name_change(e):
        nonlocal debounce
        if debounce is not None:
            debounce.deactivate()
        debounce = ui.timer(0.3, lambda: do_search(e.value), once=True)

    await header()

    with ui.column():
        ui.input(label=_("search_verb"), placeholder=_("search_placeholder"), on_change=name_change)

    loading = ui.spinner(size="lg")
    loading.set_visibility(False)

    result_list([], [])


@app.get("/plexdlweb.webmanifest")
def manifest():
    return {
        "name": "PlexDLWeb",
        "short_name": "Volume",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#282a2d",
        "theme_color": "#000",
        "icons": [
            {
                "src": "https://domino.zdimension.fr/apps/pmp-icon-1.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }


@app.get("/sw.js")
def sw():
    return """
    self.addEventListener('install', function(event) {});
    self.addEventListener('fetch', function(event) {});
    self.addEventListener('activate', function(event) {});
    """


ui.run(host=config.host, port=config.port, show=False, storage_secret=config.secret)
