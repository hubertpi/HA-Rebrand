"""Validate Android/PWA metadata and public PNG delivery without file access."""

import base64
import io
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.components import frontend
from PIL import Image

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry
from custom_components.ha_rebrand_local.branding import Branding, load_branding
from custom_components.ha_rebrand_local.const import DOMAIN
from custom_components.ha_rebrand_local.mobile import (
    ICON_PATH,
    IconView,
    ensure_icon_view,
    prepare_manifest,
    prepare_mobile_assets,
)


def data_uri(png):
    return "data:image/png;base64," + base64.b64encode(png).decode()


def brand(png, **values):
    return Branding(
        **{
            "name": "Facility Portal",
            "hide_foundation": True,
            "light": None,
            "dark": None,
            "favicon": data_uri(png),
            **values,
        }
    )


def test_square_icon_sizes_and_content_addresses(png):
    assets = prepare_mobile_assets(brand(png))
    assert {item["sizes"] for item in assets.icons} == {"192x192", "512x512"}
    assert assets.favicon_url.startswith(ICON_PATH)
    for item in assets.icons:
        content = assets.files[item["src"].split("/")[-1]]
        assert sha256(content).hexdigest() + ".png" == item["src"].split("/")[-1]
        with Image.open(io.BytesIO(content)) as image:
            assert f"{image.width}x{image.height}" == item["sizes"]
        assert item["purpose"] == "any"


def test_wide_logo_is_padded_without_stretching_or_cropping():
    output = io.BytesIO()
    Image.new("RGBA", (200, 50), "blue").save(output, format="PNG")
    assets = prepare_mobile_assets(brand(output.getvalue()))
    entry = next(item for item in assets.icons if item["sizes"] == "512x512")
    with Image.open(io.BytesIO(assets.files[entry["src"].split("/")[-1]])) as image:
        assert image.getbbox() == (0, 192, 512, 320)


def test_icon_url_changes_when_pixels_change(png):
    first = prepare_mobile_assets(brand(png))
    output = io.BytesIO()
    Image.new("RGBA", (8, 8), "red").save(output, format="PNG")
    second = prepare_mobile_assets(brand(output.getvalue()))
    assert first.favicon_url != second.favicon_url
    assert first.favicon_url == prepare_mobile_assets(brand(png)).favicon_url


def test_pwa_icon_can_differ_from_tab_favicon(png):
    output = io.BytesIO()
    Image.new("RGBA", (8, 8), "red").save(output, format="PNG")
    assets = prepare_mobile_assets(brand(png, pwa_icon=data_uri(output.getvalue())))
    with Image.open(io.BytesIO(assets.files[assets.icons[0]["src"].split("/")[-1]])) as image:
        assert image.getpixel((96, 96)) == (255, 0, 0, 255)
    with Image.open(io.BytesIO(assets.files[assets.favicon_url.split("/")[-1]])) as image:
        assert image.getpixel((32, 32)) != (255, 0, 0, 255)


def test_loading_logo_fallback_and_pwa_disabled(png):
    settings = brand(png, favicon=None, light=data_uri(png))
    assert prepare_mobile_assets(settings).icons is not None
    disabled = prepare_mobile_assets(replace(settings, pwa_enabled=False))
    assert disabled.icons is None
    assert disabled.files == {}


def test_manifest_restoration_preserves_identity_and_unrelated_fields(harness, png):
    original = deepcopy(frontend.MANIFEST_JSON.manifest)
    assets = prepare_mobile_assets(brand(png))
    manifest = prepare_manifest(brand(png), assets)
    manifest.install()
    assert frontend.MANIFEST_JSON["name"] == "Facility Portal"
    assert frontend.MANIFEST_JSON["short_name"] == "Facility Portal"
    for key in original.keys() - {"name", "short_name", "icons"}:
        assert frontend.MANIFEST_JSON[key] == original[key]
    manifest.restore()
    assert frontend.MANIFEST_JSON.manifest == original


def test_manifest_restoration_preserves_later_changes(harness, png, caplog):
    manifest = prepare_manifest(brand(png), prepare_mobile_assets(brand(png)))
    manifest.install()
    frontend.add_manifest_json_key("name", "Later owner")
    manifest.restore()
    assert frontend.MANIFEST_JSON["name"] == "Later owner"
    assert "leaving that value intact" in caplog.text


def test_pwa_setting_can_use_local_file_without_changing_loading_logo(tmp_path, png):
    folder = tmp_path / "ha_rebrand_local"
    folder.mkdir()
    (folder / "app.png").write_bytes(png)
    config = load_branding(str(tmp_path), {"pwa_icon": "app.png"})
    assert config.pwa_icon is not None
    assert config.light is None


async def test_native_public_view_registration_is_idempotent(png):
    app = web.Application()
    hass = SimpleNamespace(data={}, is_stopping=False)
    hass.http = SimpleNamespace(register_view=lambda view: view.register(hass, app, app.router))
    ensure_icon_view(hass)
    count = len(tuple(app.router.routes()))
    ensure_icon_view(hass)
    assert len(tuple(app.router.routes())) == count
    assets = prepare_mobile_assets(brand(png))
    hass.data[DOMAIN] = SimpleNamespace(mobile=assets)
    assert IconView.requires_auth is False
    async with TestClient(TestServer(app)) as client:
        response = await client.get(assets.favicon_url)
        assert response.status == 200
        assert response.content_type == "image/png"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "immutable" in response.headers["Cache-Control"]
        assert (await response.read()).startswith(b"\x89PNG")
        assert (await client.post(assets.favicon_url)).status == 405
        assert (await client.get(ICON_PATH + "configuration.yaml")).status == 404
        hass.data.pop(DOMAIN)
        assert (await client.get(assets.favicon_url)).status == 404


async def test_live_manifest_icons_favicon_and_full_cleanup(login_harness, tmp_path, png):
    hass, _, app = login_harness
    original = deepcopy(frontend.MANIFEST_JSON.manifest)
    folder = tmp_path / "ha_rebrand_local"
    folder.mkdir()
    (folder / "favicon.png").write_bytes(png)
    entry = SimpleNamespace(options={"favicon": "favicon.png", "brand_name": "Facility Portal"})
    async with TestClient(TestServer(app)) as client:
        await async_setup_entry(hass, entry)
        manifest = await (await client.get("/manifest.json")).json()
        assert manifest["name"] == "Facility Portal"
        assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}
        for icon in manifest["icons"]:
            response = await client.get(icon["src"])
            assert response.status == 200
            assert response.content_type == "image/png"
        for path in ["/", "/auth/authorize"]:
            text = await (await client.get(path)).text()
            assert 'rel="icon" type="image/png" href="/api/ha_rebrand_local/icon/' in text
            assert 'rel="apple-touch-icon" href="/api/ha_rebrand_local/icon/' in text
            assert 'href="/static/icons/favicon.ico"' not in text
        await async_unload_entry(hass, entry)
        assert frontend.MANIFEST_JSON.manifest == original
        assert (await client.get(manifest["icons"][0]["src"])).status == 404
        assert (await (await client.get("/manifest.json")).json()) == original
