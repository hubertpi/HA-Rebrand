"""Brand only the existing static authorization HTML, with reversible ownership."""

import json
import logging
import re
from dataclasses import dataclass
from functools import partial
from html import escape
from pathlib import Path

import hass_frontend
from aiohttp import web
from homeassistant.components.http.server import _serve_file

from .branding import Branding, CompatibilityError

_LOGGER = logging.getLogger(__name__)
_LOGIN_LOGO = re.compile(
    r'<img\b(?=[^>]*\bsrc=["\']/static/icons/favicon-192x192\.png["\'])[^>]*>', re.IGNORECASE
)


# HA 2026.10.4 renders the welcome heading as a text node in light DOM. Modify
# that node rather than replacing its parent (which would break Lit's markers).
# Match only the welcome text; MFA headings, warnings and all inputs stay alone.
HEADING_SCRIPT = r"""(()=>{
  "use strict";
  const heading=__HEADING_JSON__;
  const host=document.querySelector("ha-authorize");
  if(!host)return;
  const apply=()=>{
    for(const title of host.querySelectorAll("ha-auth-flow h1")){
      const walker=document.createTreeWalker(title,NodeFilter.SHOW_TEXT);
      let node;
      while((node=walker.nextNode())){
        if(node.nodeValue.trim()==="Welcome home!"){
          const next=node.nodeValue.replace("Welcome home!",heading);
          if(next!==node.nodeValue)node.nodeValue=next;
        }
      }
    }
  };
  const observer=new MutationObserver(apply);
  observer.observe(host,{childList:true,characterData:true,subtree:true});
  apply();
  window.addEventListener("pagehide",()=>observer.disconnect());
  window.addEventListener("pageshow",event=>{
    if(event.persisted){
      observer.observe(host,{childList:true,characterData:true,subtree:true});
      apply();
    }
  });
})();"""


def transform_login_html(html: str, branding: Branding) -> str:
    """Retain all stock auth bootstrap code and add presentation-only changes."""
    if not branding.login_enabled:
        return html
    if html.count("</head>") != 1 or html.count("</body>") != 1 or "<ha-authorize>" not in html:
        raise CompatibilityError("Home Assistant login page markers changed")
    match = _LOGIN_LOGO.search(html)
    if match is None:
        raise CompatibilityError("Home Assistant login logo changed")
    html = re.sub(
        r"<title>Home Assistant</title>",
        lambda _: f"<title>{escape(branding.name, quote=True)}</title>",
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    # Recompute the logo offset after changing a potentially different-length title.
    match = _LOGIN_LOGO.search(html)
    light = branding.login_light or branding.login_dark
    if light:
        source = (
            f'<source media="(prefers-color-scheme: dark)" srcset="{branding.login_dark}">'
            if branding.login_dark
            else ""
        )
        picture = (
            f'<picture id="ha-rebrand-local-login-logo">{source}'
            f'<img src="{light}" alt="{escape(branding.name, quote=True)}"></picture>'
        )
        html = html[: match.start()] + picture + html[match.end() :]
        style = (
            '<style id="ha-rebrand-local-login-style">'
            ".header #ha-rebrand-local-login-logo{display:flex;justify-content:center;max-width:80vw;}"
            f".header #ha-rebrand-local-login-logo img{{width:{branding.login_logo_width}px;"
            "height:auto;max-width:min(80vw,400px);max-height:30vh;object-fit:contain;display:block;}"
            "</style>"
        )
        html = html.replace("</head>", style + "</head>", 1)
    if branding.favicon:
        # Match icon link elements only, never the stock login header image.
        html = re.sub(
            r'<link\b(?=[^>]*\brel=["\'](?:shortcut\s+)?icon["\'])[^>]*>',
            "",
            html,
            flags=re.IGNORECASE,
        )
        html = html.replace(
            "</head>",
            f'<link rel="icon" type="image/png" href="{branding.favicon}"></head>',
            1,
        )
    if branding.touch_icon:
        html = html.replace(
            "</head>", f'<link rel="apple-touch-icon" href="{branding.touch_icon}"></head>', 1
        )
    if branding.login_heading:
        literal = (
            json.dumps(branding.login_heading)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
        script = HEADING_SCRIPT.replace("__HEADING_JSON__", literal)
        html = html.replace(
            "</body>", f'<script id="ha-rebrand-local-login-heading">{script}</script></body>', 1
        )
    return html


@dataclass
class LoginHook:
    """Retain the original route object and handler for exact restoration."""

    route: object
    original: object
    handler: object

    def install(self):
        if self.route.handler is not self.original:
            raise CompatibilityError("Another component changed the login page during setup")
        self.route._handler = self.handler

    def restore(self):
        if self.route.handler is self.handler:
            self.route._handler = self.original
        else:
            _LOGGER.warning(
                "Another component replaced the login page handler; restart Core to finish cleanup"
            )


async def prepare_login_hook(hass, branding: Branding) -> LoginHook | None:
    """Prepare an adapter for the known static GET route without changing it yet."""
    if not branding.login_enabled:
        return None
    routes = [
        route
        for route in hass.http.app.router.routes()
        if route.method == "GET" and route.resource.canonical == "/auth/authorize"
    ]
    if len(routes) != 1:
        raise CompatibilityError("Cannot locate the Home Assistant login page route")
    route = routes[0]
    original = route.handler
    expected_path = hass_frontend.where() / "authorize.html"
    if (
        not isinstance(original, partial)
        or original.func is not _serve_file
        or len(original.args) != 1
        or Path(original.args[0]) != expected_path
    ):
        raise CompatibilityError(
            "Login branding requires the standard Home Assistant static login page"
        )
    html = await hass.async_add_executor_job(expected_path.read_text, "utf-8")
    branded_html = transform_login_html(html, branding)

    async def handler(request):
        # Delegate first. Do not inspect cookies, query parameters, bodies,
        # passwords, provider choices, tokens, redirects or flow responses.
        response = await original(request)
        if (
            request.method != "GET"
            or response.status != 200
            or response.prepared
            or not isinstance(response, web.FileResponse)
            or response._path != expected_path
        ):
            return response
        headers = response.headers.copy()
        for key in (
            "Content-Length",
            "Content-Type",
            "Content-Encoding",
            "ETag",
            "Last-Modified",
            "Accept-Ranges",
            "Content-Range",
        ):
            headers.popall(key, None)
        headers["Cache-Control"] = "no-store"
        return web.Response(
            text=branded_html, content_type="text/html", charset="utf-8", headers=headers
        )

    return LoginHook(route, original, handler)
