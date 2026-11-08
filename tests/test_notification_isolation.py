"""Ensure presentation branding never installs HTML5 notification hooks."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry


@pytest.mark.parametrize("html5_loaded", [False, True])
async def test_setup_and_unload_leave_html5_and_component_listeners_untouched(
    login_harness, tmp_path, png, monkeypatch, html5_loaded
):
    hass, _, _ = login_harness
    if html5_loaded:
        hass.config.components.add("html5")
    # Represent an already-loaded platform without importing optional push
    # dependencies. Every attribute must survive branding setup and unload.
    platform = ModuleType("homeassistant.components.html5.notify")
    platform.DEFAULT_ICON = "/stock-icon.png"
    platform.DEFAULT_BADGE = "/stock-badge.png"
    original_webpush = AsyncMock()
    platform.HTML5NotifyEntity = type("HTML5NotifyEntity", (), {"_webpush": original_webpush})
    monkeypatch.setitem(sys.modules, platform.__name__, platform)
    loader = AsyncMock(side_effect=AssertionError("Must not load HTML5"))
    monkeypatch.setattr("homeassistant.loader.async_get_integration", loader)
    hass.bus.async_listen = Mock()
    directory = tmp_path / "ha_rebrand_local"
    directory.mkdir()
    (directory / "icon.png").write_bytes(png)
    entry = SimpleNamespace(options={"favicon": "icon.png"})
    for operation in (async_setup_entry, async_unload_entry):
        await operation(hass, entry)
        assert platform.DEFAULT_ICON == "/stock-icon.png"
        assert platform.DEFAULT_BADGE == "/stock-badge.png"
        assert platform.HTML5NotifyEntity._webpush is original_webpush
        loader.assert_not_called()
        hass.bus.async_listen.assert_not_called()
