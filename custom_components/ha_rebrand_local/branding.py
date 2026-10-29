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


class LogoWidthError(ValueError):
    """The configured loading logo width is outside the supported range."""


class LoginHeadingError(ValueError):
    """The configured login heading is not printable English text."""


class LoginWidthError(ValueError):
    """The configured login logo width is outside the supported range."""


@dataclass(frozen=True)
class Branding:
    """Immutable, validated public branding values."""

    name: str
    hide_foundation: bool
    light: str | None
    dark: str | None
    favicon: str | None
    logo_width: int = DEFAULTS["logo_width"]
    login_enabled: bool = DEFAULTS["login_enabled"]
    login_heading: str = DEFAULTS["login_heading"]
    login_light: str | None = None
    login_dark: str | None = None
    login_logo_width: int = DEFAULTS["login_logo_width"]
    pwa_enabled: bool = DEFAULTS["pwa_enabled"]
    pwa_icon: str | None = None
    touch_icon: str | None = None


def load_branding(config_directory: str, options: dict) -> Branding:
    """Validate settings and load assets in an executor."""
    values = {**DEFAULTS, **options}
    width = values["logo_width"]
    if type(width) not in (int, float) or not 96 <= width <= 800 or int(width) != width:
        raise LogoWidthError("Logo width must be a whole number between 96 and 800 pixels")
    name = values["brand_name"]
    if (
        not isinstance(name, str)
        or not 1 <= len(name.strip()) <= 80
        or any(ord(character) < 32 or ord(character) > 126 for character in name)
    ):
        raise ValueError("Brand name must contain 1 to 80 printable English characters")
    if any(
        type(values[key]) is not bool
        for key in ("enabled", "hide_foundation", "login_enabled", "pwa_enabled")
    ):
        raise ValueError("Branding toggles must be boolean")
    light = read_asset(config_directory, values["logo_light"])
    dark = read_asset(config_directory, values["logo_dark"])
    heading = values["login_heading"]
    login_width = values["login_logo_width"]
    login_light, login_dark = None, None
    if values["login_enabled"]:
        if (
            not isinstance(heading, str)
            or len(heading) > 80
            or any(ord(c) < 32 or ord(c) > 126 for c in heading)
        ):
            raise LoginHeadingError(
                "Login heading must contain up to 80 printable English characters"
            )
        if (
            type(login_width) not in (int, float)
            or not 96 <= login_width <= 800
            or int(login_width) != login_width
        ):
            raise LoginWidthError(
                "Login logo width must be a whole number between 96 and 800 pixels"
            )
        if values["login_logo_light"] or values["login_logo_dark"]:
            login_light = read_asset(config_directory, values["login_logo_light"])
            login_dark = read_asset(config_directory, values["login_logo_dark"])
        else:
            login_light, login_dark = light, dark
    return Branding(
        name.strip(),
        values["hide_foundation"],
        light,
        dark,
        read_asset(config_directory, values["favicon"]),
        int(width),
        values["login_enabled"],
        heading.strip() if values["login_enabled"] else "",
        login_light,
        login_dark,
        int(login_width) if values["login_enabled"] else 320,
        values["pwa_enabled"],
        read_asset(config_directory, values["pwa_icon"]) if values["pwa_enabled"] else None,
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
            f'<img class="ha-logo" src="{light}" alt="{name}"></picture>'
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
    if light:
        styles += (
            "#ha-rebrand-local-logo{display:flex;justify-content:center;max-width:80vw;}"
            f"#ha-launch-screen #ha-rebrand-local-logo .ha-logo{{width:{branding.logo_width}px;"
            "height:auto;max-width:80vw;max-height:40vh;display:block;}"
        )
    if branding.hide_foundation:
        styles += "#ha-launch-screen .ohf-logo{visibility:hidden!important;}"
    additions = f'<style id="ha-rebrand-local-style">{styles}</style>'
    if branding.favicon:
        html = re.sub(r'<link\b(?=[^>]*\brel=["\']icon["\'])[^>]*>', "", html, flags=re.IGNORECASE)
        additions += f'<link rel="icon" type="image/png" href="{branding.favicon}">'
    if branding.touch_icon:
        html = re.sub(
            r'<link\b(?=[^>]*\brel=["\'](?:apple-touch-icon|mask-icon)["\'])[^>]*>',
            "",
            html,
            flags=re.IGNORECASE,
        )
        additions += f'<link rel="apple-touch-icon" href="{branding.touch_icon}">'
    if branding.pwa_enabled:
        html = re.sub(
            r'(<meta\b(?=[^>]*\bname=["\'](?:application-name|apple-mobile-web-app-title)["\'])[^>]*\bcontent=)["\'][^"\']*["\']',
            lambda match: match.group(1) + '"' + name + '"',
            html,
            flags=re.IGNORECASE,
        )
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
