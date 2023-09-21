from datetime import timedelta

import humanize
from fastapi import Request
from fastapi.responses import RedirectResponse, FileResponse
from nicegui import ui, app, globals as ng_globals
from plexapi.collection import *
from plexapi.video import *

from config import config
from login import check_login, logout
from plex import get_server, get_self
from locales import _


@app.middleware("http")
async def check_auth(request: Request, call_next):
    # https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py
    if not check_login():
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


def header():
    """
    Displays thecommon page header
    """
    user = get_self()

    with ui.row():
        ui.button(_("home"), on_click=lambda: ui.open("/"))
        ui.button(_("logout"), on_click=logout)
        ui.label(_("user", user=user.email))


@app.get("/download/{key}")
def download(key: int):
    """
    Downloads the specified media from Plex
    """
    p = get_server().fetchItem(key)
    part = next(p.iterParts())  # TODO: handle multi versions
    filename = os.path.basename(part.file)
    return FileResponse(part.file, filename=filename, stat_result=os.stat(part.file))


@ui.page("/", title="PlexDLWeb")
def index():
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
                lambda m: m.title,
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

                def handler():
                    del query[i:]
                    clicked(part)

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
                        part = next(r.iterParts())
                        dur = timedelta(milliseconds=part.duration)
                        if dur > timedelta(hours=1):
                            dur = f"{dur.seconds // 3600}h{(dur.seconds // 60) % 60}m"
                        elif dur > timedelta(minutes=5):
                            dur = f"{dur.seconds // 60}m"
                        else:
                            dur = f"{dur.seconds // 60}m{dur.seconds % 60}s"
                        fake_button_label(dur).classes(add="ml-auto self-center").style(
                            "text-transform: none; font-size: 90%")
                        fake_button_label(humanize.naturalsize(part.size)).classes(add="mx-0 self-center").style(
                            "font-size: 90%")
                        ui.button(icon="download").props("flat").on("click.stop", lambda: ui.download(
                            f"/download/{r.ratingKey}")).classes(add="px-3")

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

    def do_search(query, force=False):
        nonlocal last_search
        previous, last_search = last_search, query
        if not force and query == previous or len(query) < 3:
            return

        results = server.search(query)
        result_list.refresh([query], results)

    debounce = None

    def name_change(e):
        nonlocal debounce
        if debounce is not None:
            debounce.deactivate()
        debounce = ui.timer(0.3, lambda: do_search(e.value), once=True)

    server = get_server()

    header()

    with ui.column():
        ui.input(label=_("search_verb"), placeholder=_("search_placeholder"), on_change=name_change)

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