"""Native PWA manifest metadata and same-origin, content-addressed PNG icons."""

import base64
import io
import logging
from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView
from PIL import Image, ImageOps

from .branding import Branding
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
ICON_PATH = "/api/ha_rebrand_local/icon/"
VIEW_REGISTERED = f"{DOMAIN}_icon_view_registered"


@dataclass
class MobileAssets:
    """Only generated PNG bytes and their public display metadata."""

    files: dict[str, bytes]
    icons: list[dict] | None
    favicon_url: str | None
    touch_url: str | None


def prepare_mobile_assets(branding: Branding) -> MobileAssets:
    """Generate mobile-compatible square PNGs from already validated images."""
    files = {}

    def icon(data_uri, size):
        data = base64.b64decode(data_uri.split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(data)) as image:
            scaled = ImageOps.contain(image.convert("RGBA"), (size, size), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size))
            canvas.alpha_composite(
                scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2)
            )
        output = io.BytesIO()
        canvas.save(output, format="PNG")
        content = output.getvalue()
        filename = sha256(content).hexdigest() + ".png"
        files[filename] = content
        return ICON_PATH + filename

    favicon_url = icon(branding.favicon, 64) if branding.favicon else None
    source = branding.pwa_icon or branding.favicon or branding.light or branding.dark
    icons = None
    touch_url = None
    if branding.pwa_enabled and source:
        icons = [
            {
                "src": icon(source, size),
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any",
            }
            for size in (192, 512)
        ]
        touch_url = icon(source, 180)
    elif branding.favicon:
        touch_url = icon(branding.favicon, 180)
    return MobileAssets(files, icons, favicon_url, touch_url)


def with_mobile_urls(branding: Branding, assets: MobileAssets) -> Branding:
    """Keep loading logos embedded but use normal PNG URLs for browser icons."""
    return replace(branding, favicon=assets.favicon_url, touch_icon=assets.touch_url)


class IconView(HomeAssistantView):
    """Serve generated public branding pixels; never read a requested file path."""

    url = ICON_PATH + "{filename}"
    name = "api:ha_rebrand_local:icon"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request, filename):
        runtime = self.hass.data.get(DOMAIN)
        assets = getattr(runtime, "mobile", None)
        content = assets.files.get(filename) if assets else None
        if content is None:
            raise web.HTTPNotFound()
        return web.Response(
            body=content,
            content_type="image/png",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Content-Type-Options": "nosniff",
            },
        )


def ensure_icon_view(hass):
    """Use HA's registration API once per process; inactive views return 404."""
    if not hass.data.get(VIEW_REGISTERED):
        hass.http.register_view(IconView(hass))
        hass.data[VIEW_REGISTERED] = True


@dataclass
class ManifestBranding:
    """Restore only manifest fields still owned by this integration."""

    original: dict
    installed: dict

    def install(self):
        for key, value in self.installed.items():
            frontend.add_manifest_json_key(key, deepcopy(value))

    def restore(self):
        for key, value in self.installed.items():
            if frontend.MANIFEST_JSON[key] == value:
                frontend.add_manifest_json_key(key, deepcopy(self.original[key]))
            else:
                _LOGGER.warning(
                    "Another component changed the web app manifest %s; leaving that value intact",
                    key,
                )


def prepare_manifest(branding: Branding, assets: MobileAssets) -> ManifestBranding:
    """Preserve HA's app identity, start URL, scope, permissions and theme fields."""
    installed = {}
    if branding.pwa_enabled:
        installed = {"name": branding.name, "short_name": branding.name}
        if assets.icons:
            installed["icons"] = assets.icons
    original = {key: deepcopy(frontend.MANIFEST_JSON[key]) for key in installed}
    return ManifestBranding(original, installed)
