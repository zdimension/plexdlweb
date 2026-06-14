from nicegui import app
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
import httpx
from config import config
from common import io_bound


def _clean_token(token: str | None, name: str) -> str:
    if not isinstance(token, str) or not token.strip():
        raise ValueError(f"{name} is missing")
    return token.strip()


@app.on_startup
async def startup():
    app.state.httpx_client = httpx.AsyncClient()


@app.on_shutdown
async def shutdown():
    await app.state.httpx_client.aclose()


@app.get("/plex/{path:path}")
async def streaming(path: str) -> StreamingResponse:
    """
    Forwards a request to the Plex server
    """
    # https://stackoverflow.com/a/74556972/2196124
    client = app.state.httpx_client
    url = httpx.URL(config.server_url + "/" + path)
    req = httpx.Request("GET", url, headers={"X-Plex-Token": app.storage.user.get("server_token")})
    resp = await client.send(req, stream=True)
    return StreamingResponse(
        resp.aiter_raw(),
        status_code=resp.status_code,
        headers=resp.headers,
        background=BackgroundTask(resp.aclose)
    )


async def get_server():
    token = _clean_token(app.storage.user.get("server_token"), "server token")
    return await io_bound(PlexServer, config.server_url, token)


async def get_self():
    token = _clean_token(app.storage.user.get("user_token"), "user token")
    return await io_bound(MyPlexAccount, token=token)


async def get_server_token(user_token: str) -> str:
    user_token = _clean_token(user_token, "user token")
    acc = await io_bound(MyPlexAccount, token=user_token)
    srv = [r for r in await io_bound(acc.resources) if r.clientIdentifier == config.server_id][0]
    return _clean_token(srv.accessToken, "server token")


async def check_user_token(token: str) -> bool:
    try:
        token = _clean_token(token, "user token")
        await io_bound(MyPlexAccount, token=token)
        return True
    except Exception as e:
        print(e)
        return False


async def check_server_token(token: str) -> bool:
    try:
        token = _clean_token(token, "server token")
        await io_bound(PlexServer, config.server_url, token=token)
        return True
    except Exception as e:
        print(e)
        return False
