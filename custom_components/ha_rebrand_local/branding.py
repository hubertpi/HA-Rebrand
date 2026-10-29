"""Apply narrowly scoped branding after Jinja rendering, never to its source."""

import json
import logging
import re
from dataclasses import dataclass
from html import escape

import jinja2

from .assets import read_asset
from .const import DEFAULTS

_LOGGER = logging.getLogger(__name__)
_LOGO = re.compile(
    r'<img\b(?=[^>]*\bclass=["\']ha-logo["\'])(?=[^>]*\bsrc=["\']/static/images/home-assistant-logo-loading\.svg["\'])[^>]*>',
    re.IGNORECASE,
)
_TITLE = re.compile(r"<title>Home Assistant</title>", re.IGNORECASE)
_LAUNCH = re.compile(r'<div\s+id=["\']ha-launch-screen["\']\s*>', re.IGNORECASE)


class CompatibilityError(ValueError):
    """The HA loading template no longer matches the supported structure."""


@dataclass(frozen=True)
class Branding:
    """Immutable, validated public branding values."""

    name: str
    hide_foundation: bool
    light: str | None
    dark: str | None
    favicon: str | None


def load_branding(config_directory: str, options: dict) -> Branding:
    """Validate settings and load assets in an executor."""
    values = {**DEFAULTS, **options}
    name = values["brand_name"]
    if (
        not isinstance(name, str)
        or not 1 <= len(name.strip()) <= 80
        or any(ord(character) < 32 or ord(character) > 126 for character in name)
    ):
        raise ValueError("Brand name must contain 1 to 80 printable English characters")
    if type(values["enabled"]) is not bool or type(values["hide_foundation"]) is not bool:
        raise ValueError("Branding toggles must be boolean")
    return Branding(
        name.strip(),
        values["hide_foundation"],
        read_asset(config_directory, values["logo_light"]),
        read_asset(config_directory, values["logo_dark"]),
        read_asset(config_directory, values["favicon"]),
    )


def transform_html(html: str, branding: Branding) -> str:
    """Replace only the known launch logo, title and launch attribution style."""
    launch = _LAUNCH.search(html)
    if launch is None or html.count("</head>") != 1:
        raise CompatibilityError("Home Assistant launch screen markers changed")
    logo = _LOGO.search(html, launch.end())
    app = html.find("<home-assistant", launch.end())
    if logo is None or app == -1 or logo.start() > app or not _TITLE.search(html):
        raise CompatibilityError("Home Assistant launch logo or title changed")
    if branding.hide_foundation and not re.search(
        r'class=["\']ohf-logo["\']', html[launch.end() : app]
    ):
        raise CompatibilityError("Home Assistant attribution structure changed")
    name = escape(branding.name, quote=True)
    light = branding.light or branding.dark
    replacement = logo.group()
    if light:
        source = (
            f'<source media="(prefers-color-scheme: dark)" srcset="{branding.dark}">'
            if branding.dark
            else ""
        )
        replacement = (
            f'<picture id="ha-rebrand-local-logo">{source}'
            f'<img class="ha-logo" src="{light}" alt="{name}" width="96" height="96"></picture>'
        )
    else:
        replacement = replacement.replace('alt="Home Assistant"', f'alt="{name}"')
    if branding.name != DEFAULTS["brand_name"]:
        replacement += f'<span id="ha-rebrand-local-name">{name}</span>'
    html = html[: logo.start()] + replacement + html[logo.end() :]
    html = _TITLE.sub(lambda _: f"<title>{name}</title>", html, count=1)
    styles = (
        "#ha-launch-screen .ha-logo{object-fit:contain;}"
        "#ha-launch-screen .ha-lockup{flex-direction:column;gap:20px;max-width:90vw;text-align:center;}"
        "#ha-rebrand-local-name{font-size:clamp(20px,4vw,36px);overflow-wrap:anywhere;}"
    )
    if branding.hide_foundation:
        styles += "#ha-launch-screen .ohf-logo{visibility:hidden!important;}"
    additions = f'<style id="ha-rebrand-local-style">{styles}</style>'
    if branding.favicon:
        html = re.sub(r'<link\b(?=[^>]*\brel=["\']icon["\'])[^>]*>', "", html, flags=re.IGNORECASE)
        additions += f'<link rel="icon" type="image/png" href="{branding.favicon}">'
    if branding.name != DEFAULTS["brand_name"]:
        # The name is serialized for an HTML script context, not interpolated as code.
        literal = (
            json.dumps(branding.name)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
        additions += (
            '<script id="ha-rebrand-local-title">(()=>{const name=' + literal + ";"
            'const title=document.querySelector("title");if(!title)return;'
            "const apply=()=>{if(title.textContent!==name)title.textContent=name;};"
            "new MutationObserver(apply).observe(title,{childList:true,characterData:true,subtree:true});"
            "apply();})();</script>"
        )
    return html.replace("</head>", additions + "</head>", 1)


class BrandedTemplate(jinja2.Template):
    """Wrap one index template without changing global Jinja or HA methods."""

    def __new__(cls, original: jinja2.Template, branding: Branding):
        return super().__new__(cls, "")

    def __init__(self, original: jinja2.Template, branding: Branding):
        self.original = original
        self.branding = branding
        self.failed = False

    def render(self, *args, **kwargs) -> str:
        html = self.original.render(*args, **kwargs)
        if self.failed:
            return html
        try:
            return transform_html(html, self.branding)
        except Exception:
            self.failed = True
            _LOGGER.exception(
                "HA Rebrand could not customize the launch screen; serving original HTML"
            )
            return html
