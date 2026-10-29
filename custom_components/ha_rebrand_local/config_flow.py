"""English-only native configuration and options flow for HA Rebrand."""

import probatio as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.core import callback

from .assets import AssetError
from .branding import load_branding
from .const import DEFAULTS, DOMAIN, NAME


def schema(values):
    """Allow clearing optional filenames by leaving them blank."""
    return vol.Schema(
        {
            vol.Required("enabled", default=values["enabled"]): bool,
            vol.Required("brand_name", default=values["brand_name"]): str,
            vol.Required("hide_foundation", default=values["hide_foundation"]): bool,
            vol.Optional("logo_light", default=values["logo_light"]): str,
            vol.Optional("logo_dark", default=values["logo_dark"]): str,
            vol.Optional("favicon", default=values["favicon"]): str,
        }
    )


async def validate(hass, user_input):
    """Validate local images before committing options."""
    try:
        if user_input.get("enabled", True):
            await hass.async_add_executor_job(load_branding, hass.config.config_dir, user_input)
    except AssetError:
        return {"base": "invalid_asset"}
    except ValueError:
        return {"brand_name": "invalid_name"}
    return {}


class RebrandConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one instance through Home Assistant's authenticated UI."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RebrandOptionsFlow()

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            errors = await validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title=NAME, data={}, options={**DEFAULTS, **user_input}
                )
        return self.async_show_form(
            step_id="user", data_schema=schema({**DEFAULTS, **(user_input or {})}), errors=errors
        )


class RebrandOptionsFlow(OptionsFlowWithReload):
    """Reload the integration automatically when options change."""

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Missing optional fields mean clear, not retain an old filename.
            user_input = {**DEFAULTS, **user_input}
            errors = await validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(data=user_input)
        values = {**DEFAULTS, **self.config_entry.options, **(user_input or {})}
        return self.async_show_form(step_id="init", data_schema=schema(values), errors=errors)
