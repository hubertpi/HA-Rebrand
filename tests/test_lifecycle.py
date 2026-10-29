"""Exercise actual Core IndexView HTTP responses and integration rollback."""

from types import SimpleNamespace

import pytest
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.exceptions import ConfigEntryError

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry
from custom_components.ha_rebrand_local.branding import BrandedTemplate
from custom_components.ha_rebrand_local.const import DOMAIN


def entry(**options):
    return SimpleNamespace(options=options)


async def test_real_http_setup_unload_and_auth_untouched(harness):
    hass, view, app = harness
    routes_before = tuple(app.router.routes())
    original = view.get_template()
    config = entry(brand_name="Facility Control")
    assert await async_setup_entry(hass, config)
    assert isinstance(view._template_cache, BrandedTemplate)
    assert tuple(app.router.routes()) == routes_before
    async with TestClient(TestServer(app)) as client:
        response = await client.get("/")
        assert response.status == 200
        assert response.content_type == "text/html"
        html = await response.text()
        assert "<title>Facility Control</title>" in html
        assert "visibility:hidden!important" in html
        assert await (await client.get("/auth/authorize")).text() == "original authorization route"
        assert "<title>Facility Control</title>" in await (await client.get("/lovelace")).text()
        assert await async_unload_entry(hass, config)
        assert view._template_cache is original
        restored = await (await client.get("/")).text()
        assert "<title>Home Assistant</title>" in restored
        assert "ha-rebrand-local-style" not in restored
        assert await (await client.get("/auth/authorize")).text() == "original authorization route"
        assert tuple(app.router.routes()) == routes_before


async def test_repeated_reload_has_no_nested_wrappers(harness):
    hass, view, _ = harness
    original = view.get_template()
    for index in range(5):
        config = entry(brand_name=f"Name {index}")
        await async_setup_entry(hass, config)
        assert view._template_cache.original is original
        assert await async_unload_entry(hass, config)
        assert view._template_cache is original


async def test_disabled_and_safe_mode_leave_template_alone(harness):
    hass, view, _ = harness
    original = view.get_template()
    await async_setup_entry(hass, entry(enabled=False, logo_light="missing.png"))
    assert view._template_cache is original
    assert DOMAIN not in hass.data
    await async_unload_entry(hass, entry())
    hass.config.safe_mode = True
    await async_setup_entry(hass, entry())
    assert view._template_cache is original


async def test_setup_failure_leaves_original_template(harness):
    hass, view, _ = harness
    original = view.get_template()
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry(logo_light="missing.png"))
    assert view._template_cache is original
    assert DOMAIN not in hass.data


async def test_duplicate_setup_rejected(harness):
    hass, view, _ = harness
    await async_setup_entry(hass, entry())
    wrapper = view._template_cache
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry())
    assert view._template_cache is wrapper


async def test_third_party_hook_not_overwritten_on_unload(harness, caplog):
    hass, view, _ = harness
    await async_setup_entry(hass, entry())
    third_party = object()
    view._template_cache = third_party
    await async_unload_entry(hass, entry())
    assert view._template_cache is third_party
    assert "restart Core" in caplog.text


async def test_frontend_development_mode_rejected(harness):
    hass, view, _ = harness
    view.repo_path = "/some/frontend"
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry())
    assert view._template_cache is None
