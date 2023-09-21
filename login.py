"""
This module uses code from https://github.com/Tautulli/Tautulli for the Plex OAuth login, licensed under GNU GPLv3.
"""
from typing import Optional

import asyncio
from nicegui import ui, app
from config import config
import json
from fastapi.responses import RedirectResponse
from plex import check_user_token, check_server_token, get_server_token
from locales import _


async def check_login() -> Optional[tuple[str, str]]:
    if (user_token := app.storage.user.get("user_token")) and (server_token := app.storage.user.get("server_token")) \
            and all(await asyncio.gather(check_user_token(user_token), check_server_token(server_token))):
        return user_token, server_token
    else:
        return None


@ui.page("/logout", title=_("logout"))
def logout():
    app.storage.user.pop("user_token")
    app.storage.user.pop("server_token")
    return RedirectResponse("/login")


@ui.page("/login", title=_("login"))
async def page_login():
    if await check_login():
        # already logged in, redirect to home
        return RedirectResponse("/")

    HEADERS = {
        "Accept": "application/json",
        "X-Plex-Product": "PlexDLWeb",
        "X-Plex-Version": "Plex OAuth",
        "X-Plex-Client-Identifier": str(config.uuid),
        "X-Plex-Platform": "PlexDLWeb",
        "X-Plex-Platform-Version": "0.1",
        "X-Plex-Model": "Plex OAuth",
        "X-Plex-Device": "PlexDLWeb",
        "X-Plex-Device-Name": "PlexDLWeb",
        "X-Plex-Device-Screen-Resolution": "1920x1080",
        "X-Plex-Language": "fr"
    }
    ui.add_body_html(f"""
        <script>
            const HEADERS = {json.dumps(HEADERS)};
        </script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js" integrity="sha512-v2CJ7UaYy4JwqLDIrZUI/4hqeoQieOmAZNXBeQyjo21dadnwR+8ZaIJVT8EE2iyI61OV8e6M8PP2/4hpQINQ/g==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    """)
    ui.add_body_html("""
        <script>
            getPlexOAuthPin = function () {
                var deferred = $.Deferred();

                $.ajax({
                    url: 'https://plex.tv/api/v2/pins?strong=true',
                    type: 'POST',
                    headers: HEADERS,
                    success: function(data) {
                        deferred.resolve({pin: data.id, code: data.code});
                    },
                    error: function() {
                        closePlexOAuthWindow();
                        deferred.reject();
                    }
                });
                return deferred;
            };

            let plex_oauth_window = null;

            function closePlexOAuthWindow() {
                if (plex_oauth_window) {
                    plex_oauth_window.close();
                }
            }

            function PopupCenter(url, title, w, h) {
                // Fixes dual-screen position                         Most browsers      Firefox
                var dualScreenLeft = window.screenLeft != undefined ? window.screenLeft : window.screenX;
                var dualScreenTop = window.screenTop != undefined ? window.screenTop : window.screenY;

                var width = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
                var height = window.innerHeight ? window.innerHeight : document.documentElement.clientHeight ? document.documentElement.clientHeight : screen.height;

                var left = ((width / 2) - (w / 2)) + dualScreenLeft;
                var top = ((height / 2) - (h / 2)) + dualScreenTop;
                var newWindow = window.open(url, title, 'scrollbars=yes, width=' + w + ', height=' + h + ', top=' + top + ', left=' + left);

                // Puts focus on the newWindow
                if (window.focus) {
                    newWindow.focus();
                }

                return newWindow;
            }

            const plex_oauth_loader = '<style>' +
                    '.login-loader-container {' +
                        'font-family: "Open Sans", Arial, sans-serif;' +
                        'position: absolute;' +
                        'top: 0;' +
                        'right: 0;' +
                        'bottom: 0;' +
                        'left: 0;' +
                    '}' +
                    '.login-loader-message {' +
                        'color: #282A2D;' +
                        'text-align: center;' +
                        'position: absolute;' +
                        'left: 50%;' +
                        'top: 25%;' +
                        'transform: translate(-50%, -50%);' +
                    '}' +
                    '.login-loader {' +
                        'border: 5px solid #ccc;' +
                        '-webkit-animation: spin 1s linear infinite;' +
                        'animation: spin 1s linear infinite;' +
                        'border-top: 5px solid #282A2D;' +
                        'border-radius: 50%;' +
                        'width: 50px;' +
                        'height: 50px;' +
                        'position: relative;' +
                        'left: calc(50% - 25px);' +
                    '}' +
                    '@keyframes spin {' +
                        '0% { transform: rotate(0deg); }' +
                        '100% { transform: rotate(360deg); }' +
                    '}' +
                '</style>' +
                '<div class="login-loader-container">' +
                    '<div class="login-loader-message">' +
                        '<div class="login-loader"></div>' +
                        '<br>' +
                        '""" + _("redirecting_to_plex") + """...' +
                    '</div>' +
                '</div>';

            function encodeData(data) {
                return Object.keys(data).map(function(key) {
                    return [key, data[key]].map(encodeURIComponent).join("=");
                }).join("&");
            }

            function PlexOAuth(success, error) {
                closePlexOAuthWindow();
                plex_oauth_window = PopupCenter('', 'Plex-OAuth', 600, 700);
                $(plex_oauth_window.document.body).html(plex_oauth_loader);

                getPlexOAuthPin().then(function (data) {
                    const pin = data.pin;
                    const code = data.code;

                    var oauth_params = {
                        'clientID': HEADERS['X-Plex-Client-Identifier'],
                        'context[device][product]': HEADERS['X-Plex-Product'],
                        'context[device][version]': HEADERS['X-Plex-Version'],
                        'context[device][platform]': HEADERS['X-Plex-Platform'],
                        'context[device][platformVersion]': HEADERS['X-Plex-Platform-Version'],
                        'context[device][device]': HEADERS['X-Plex-Device'],
                        'context[device][deviceName]': HEADERS['X-Plex-Device-Name'],
                        'context[device][model]': HEADERS['X-Plex-Model'],
                        'context[device][screenResolution]': HEADERS['X-Plex-Device-Screen-Resolution'],
                        'context[device][layout]': 'desktop',
                        'code': code
                    }

                    plex_oauth_window.location = 'https://app.plex.tv/auth/#!?' + encodeData(oauth_params);
                    polling = pin;

                    (function poll() {
                        $.ajax({
                            url: 'https://plex.tv/api/v2/pins/' + pin,
                            type: 'GET',
                            headers: HEADERS,
                            success: function (data) {
                                if (data.authToken){
                                    closePlexOAuthWindow();
                                    if (typeof success === "function") {
                                        success(data.authToken)
                                    }
                                }
                            },
                            error: function (jqXHR, textStatus, errorThrown) {
                                if (textStatus !== "timeout") {
                                    closePlexOAuthWindow();
                                    if (typeof error === "function") {
                                        error()
                                    }
                                }
                            },
                            complete: function () {
                                if (!plex_oauth_window.closed && polling === pin){
                                    setTimeout(function() {poll()}, 1000);
                                }
                            },
                            timeout: 10000
                        });
                    })();
                }, function () {
                    closePlexOAuthWindow();
                    if (typeof error === "function") {
                        error()
                    }
                });
            }

            function getToken() {
                return new Promise((resolve, reject) => {
                    PlexOAuth(function (token) {
                        resolve(token);
                    }, function () {
                        reject();
                    });
                });
            }
        </script>
    """)

    async def connect_plex():
        login_btn.text = _("logging_in")
        app.storage.user["user_token"] = await ui.run_javascript("return await getToken();", timeout=120)
        app.storage.user["server_token"] = await get_server_token(app.storage.user["user_token"])
        ui.open("/")

    with ui.column():
        login_btn = ui.button(_("login_with_plex"), on_click=connect_plex)
