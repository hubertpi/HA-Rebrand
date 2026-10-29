"""Exercise native HA config and reload-capable options flows."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.data_entry_flow import AbortFlow

from custom_components.ha_rebrand_local.config_flow import (
    RebrandConfigFlow,
    RebrandOptionsFlow,
    schema,
    validate,
)
from custom_components.ha_rebrand_local.const import DEFAULTS


def test_schema_defaults():
    assert schema(DEFAULTS)({}) == DEFAULTS


async def test_validate_invalid_name(harness):
    hass, _, _ = harness
    assert await validate(hass, {"brand_name": "bad\nname"}) == {"brand_name": "invalid_name"}


async def test_validate_missing_logo(harness):
    hass, _, _ = harness
    assert await validate(hass, {"logo_light": "missing.png"}) == {"base": "invalid_asset"}


async def test_disable_even_with_missing_logo(harness):
    hass, _, _ = harness
    assert await validate(hass, {"enabled": False, "logo_light": "missing.png"}) == {}


async def test_initial_flow(harness):
    hass, _, _ = harness
    flow = RebrandConfigFlow()
    flow.hass = hass
    with (
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(flow, "_abort_if_unique_id_configured"),
    ):
        result = await flow.async_step_user()
        assert result["type"] == "form"
        result = await flow.async_step_user({**DEFAULTS, "brand_name": "Facility Control"})
        assert result["type"] == "create_entry"
        assert result["options"]["brand_name"] == "Facility Control"
        assert result["data"] == {}


async def test_single_entry_abort(harness):
    hass, _, _ = harness
    flow = RebrandConfigFlow()
    flow.hass = hass
    with (
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(
            flow, "_abort_if_unique_id_configured", side_effect=AbortFlow("already_configured")
        ),
    ):
        with pytest.raises(AbortFlow):
            await flow.async_step_user(DEFAULTS)


def test_options_flow_uses_native_reload():
    assert isinstance(
        RebrandConfigFlow.async_get_options_flow(SimpleNamespace()), OptionsFlowWithReload
    )


async def test_options_can_clear_old_logo(harness):
    hass, _, _ = harness
    flow = RebrandOptionsFlow()
    flow.hass = hass
    with patch.object(
        type(flow),
        "config_entry",
        new_callable=lambda: property(
            lambda _: SimpleNamespace(options={**DEFAULTS, "logo_light": "old.png"})
        ),
    ):
        result = await flow.async_step_init({**DEFAULTS, "brand_name": "Updated"})
        assert result["data"]["logo_light"] == ""
        assert result["data"]["brand_name"] == "Updated"
