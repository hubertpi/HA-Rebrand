"""Verify static login presentation changes and preservation of auth routes."""

from types import SimpleNamespace

import hass_frontend
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.exceptions import ConfigEntryError

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry
from custom_components.ha_rebrand_local.branding import Branding, CompatibilityError, load_branding
from custom_components.ha_rebrand_local.const import DOMAIN
from custom_components.ha_rebrand_local.login import transform_login_html


def settings(**values):
    return SimpleNamespace(options=values)


def login_html():
    return (hass_frontend.where() / "authorize.html").read_text()


def brand(**values):
    return Branding(
        **{
            "name": "Facility Control",
            "hide_foundation": True,
            "light": None,
            "dark": None,
            "favicon": None,
            **values,
        }
    )


def test_stock_login_script_and_component_preserved():
    original = login_html()
    changed = transform_login_html(original, brand())
    assert "<ha-authorize></ha-authorize>" in changed
    assert "Welcome home!" in changed
    assert 'const heading="Welcome"' in changed
    assert "/auth/providers" in changed
    # Injected code must not remove or alter any stock script.
    import re

    for script in re.findall(r"<script\b.*?</script>", original, re.DOTALL):
        assert script in changed


def test_blank_heading_keeps_stock_text_and_disabled_returns_exact_html():
    original = login_html()
    assert (
        transform_login_html(original, brand(name="Home Assistant", login_heading="")) == original
    )
    assert transform_login_html(original, brand(login_enabled=False)) == original


def test_login_logo_light_dark_and_width():
    html = transform_login_html(
        login_html(),
        brand(
            login_light="data:image/png;base64,LIGHT",
            login_dark="data:image/png;base64,DARK",
            login_logo_width=480,
        ),
    )
    assert 'src="data:image/png;base64,LIGHT"' in html
    assert 'srcset="data:image/png;base64,DARK"' in html
    assert "width:480px;height:auto;" in html
    assert "/static/icons/favicon-192x192.png" not in html


@pytest.mark.parametrize("marker", ["<ha-authorize>", "</head>", "favicon-192x192.png"])
def test_changed_login_structure_rejected(marker):
    with pytest.raises(CompatibilityError):
        transform_login_html(login_html().replace(marker, "changed"), brand())


def test_loading_logos_reused_but_explicit_login_logo_can_differ(tmp_path, png):
    folder = tmp_path / "ha_rebrand_local"
    folder.mkdir()
    for name in ["loading.png", "login.png"]:
        (folder / name).write_bytes(png)
    shared = load_branding(str(tmp_path), {"logo_light": "loading.png"})
    assert shared.login_light == shared.light
    separate = load_branding(str(tmp_path), {"login_logo_light": "login.png"})
    assert separate.light is None
    assert separate.login_light is not None


def test_login_disable_ignores_unused_missing_assets(tmp_path):
    value = load_branding(
        str(tmp_path), {"login_enabled": False, "login_logo_light": "missing.png"}
    )
    assert not value.login_enabled


@pytest.mark.parametrize("heading", ["line\nbreak", "x" * 81, "\u4e2d\u6587"])
def test_invalid_login_heading_rejected(tmp_path, heading):
    from custom_components.ha_rebrand_local.branding import LoginHeadingError

    with pytest.raises(LoginHeadingError):
        load_branding(str(tmp_path), {"login_heading": heading})


@pytest.mark.parametrize("width", [95, 801, True, 320.5])
def test_invalid_login_width_rejected(tmp_path, width):
    from custom_components.ha_rebrand_local.branding import LoginWidthError

    with pytest.raises(LoginWidthError):
        load_branding(str(tmp_path), {"login_logo_width": width})


async def test_live_frozen_router_and_auth_endpoints_unchanged(login_harness):
    hass, view, app = login_harness

    async def auth_api(request):
        return web.Response(text=await request.text(), headers={"X-Test-Auth": "unchanged"})

    app.router.add_post("/auth/login_flow", auth_api)
    app.router.add_post("/auth/token", auth_api)
    routes = tuple(app.router.routes())
    authorize = next(route for route in routes if route.resource.canonical == "/auth/authorize")
    original_handler = authorize.handler
    original_template = view.get_template()
    async with TestClient(TestServer(app)) as client:
        assert app.router.frozen
        await async_setup_entry(hass, settings())
        assert tuple(app.router.routes()) == routes
        assert authorize is next(
            route for route in app.router.routes() if route.resource.canonical == "/auth/authorize"
        )
        response = await client.get(
            "/auth/authorize?client_id=synthetic-client&state=synthetic-state"
        )
        assert response.status == 200
        assert response.content_type == "text/html"
        assert response.headers["Cache-Control"] == "no-store"
        assert "ha-rebrand-local-login-heading" in await response.text()
        for url in ["/auth/login_flow", "/auth/token"]:
            result = await client.post(url, data="synthetic-request-body")
            assert await result.text() == "synthetic-request-body"
            assert result.headers["X-Test-Auth"] == "unchanged"
        await async_unload_entry(hass, settings())
        assert authorize.handler is original_handler
        assert view._template_cache is original_template
        restored = await (await client.get("/auth/authorize")).text()
        assert restored == login_html()
        assert tuple(app.router.routes()) == routes


async def test_disabled_login_keeps_stock_handler(login_harness):
    hass, _, app = login_harness
    route = next(
        route for route in app.router.routes() if route.resource.canonical == "/auth/authorize"
    )
    original = route.handler
    await async_setup_entry(hass, settings(login_enabled=False))
    assert route.handler is original
    assert hass.data[DOMAIN].login is None


async def test_unknown_login_handler_rejected_before_any_install(harness):
    hass, view, app = harness
    original = view.get_template()
    routes = tuple(app.router.routes())
    with pytest.raises(ConfigEntryError, match="standard Home Assistant static login"):
        await async_setup_entry(hass, settings())
    assert view._template_cache is original
    assert tuple(app.router.routes()) == routes
    assert DOMAIN not in hass.data


async def test_repeated_login_reload_restores_exact_original(login_harness):
    hass, _, app = login_harness
    route = next(
        route for route in app.router.routes() if route.resource.canonical == "/auth/authorize"
    )
    original = route.handler
    for _ in range(4):
        await async_setup_entry(hass, settings())
        assert hass.data[DOMAIN].login.original is original
        await async_unload_entry(hass, settings())
        assert route.handler is original


async def test_later_login_handler_is_not_overwritten(login_harness, caplog):
    hass, _, app = login_harness
    await async_setup_entry(hass, settings())
    route = hass.data[DOMAIN].login.route
    third_party = object()
    route._handler = third_party
    await async_unload_entry(hass, settings())
    assert route.handler is third_party
    assert "restart Core" in caplog.text


def test_configured_login_favicon_does_not_change_stock_header_logo():
    html = transform_login_html(login_html(), brand(favicon="data:image/png;base64,ICON"))
    assert '<link rel="icon" type="image/png" href="data:image/png;base64,ICON">' in html
    assert 'href="/static/icons/favicon.ico"' not in html
    assert 'src="/static/icons/favicon-192x192.png"' in html


def test_disabled_login_branding_preserves_stock_favicon():
    original = login_html()
    assert (
        transform_login_html(
            original, brand(login_enabled=False, favicon="data:image/png;base64,ICON")
        )
        == original
    )


async def test_one_favicon_setting_applies_to_both_pages_and_unloads(login_harness, tmp_path, png):
    hass, _, app = login_harness
    folder = tmp_path / "ha_rebrand_local"
    folder.mkdir()
    (folder / "favicon.png").write_bytes(png)
    entry = settings(favicon="favicon.png", brand_name="Facility Portal")
    async with TestClient(TestServer(app)) as client:
        await async_setup_entry(hass, entry)
        for url in ["/", "/auth/authorize"]:
            html = await (await client.get(url)).text()
            assert '<link rel="icon" type="image/png" href="data:image/png;base64,' in html
            assert 'href="/static/icons/favicon.ico"' not in html
            assert "<title>Facility Portal</title>" in html
        await async_unload_entry(hass, entry)
        restored = await (await client.get("/auth/authorize")).text()
        assert 'href="/static/icons/favicon.ico"' in restored
        assert "data:image/png;base64," not in restored


@pytest.mark.parametrize(
    "name",
    ["Facility Portal", "A & B <Portal>", "</title><script>window.compromised=true</script>"],
)
def test_login_tab_title_uses_safely_escaped_brand_name(name):
    import re
    from html import unescape

    html = transform_login_html(
        login_html(), brand(name=name, login_light="data:image/png;base64,LOGO")
    )
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert unescape(title) == name
    assert "</title><script>window.compromised=true</script>" not in html
    assert 'src="data:image/png;base64,LOGO"' in html
