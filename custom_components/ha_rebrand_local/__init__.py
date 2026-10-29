"""HA Rebrand: local loading screen branding with reversible cleanup."""

import logging
from dataclasses import dataclass

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .branding import BrandedTemplate, CompatibilityError, load_branding, transform_html
from .const import DEFAULTS, DOMAIN
from .login import LoginHook, prepare_login_hook

_LOGGER = logging.getLogger(__name__)


@dataclass
class Runtime:
    """Keep the exact index view, original template and our installed wrapper."""

    view: object
    original: object
    branded: BrandedTemplate
    login: LoginHook | None = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Install a wrapper on this HA instance's already loaded index template."""
    if DOMAIN in hass.data:
        raise ConfigEntryError("Only one HA Rebrand entry is supported")
    options = {**DEFAULTS, **entry.options}
    if not options["enabled"]:
        return True
    if hass.config.safe_mode:
        _LOGGER.info("HA Rebrand is inactive in safe mode")
        return True
    views = [
        resource
        for resource in hass.http.app.router.resources()
        if isinstance(resource, frontend.IndexView)
    ]
    if len(views) != 1:
        raise ConfigEntryError(
            "Cannot locate the Home Assistant index view; branding was not applied"
        )
    view = views[0]
    if view.repo_path is not None:
        raise ConfigEntryError("Frontend development repositories are not supported")
    try:
        branding = await hass.async_add_executor_job(load_branding, hass.config.config_dir, options)
        original = await hass.async_add_executor_job(view.get_template)
        if isinstance(original, BrandedTemplate):
            raise CompatibilityError("A branding wrapper is already present")
        # Verify before changing anything. All filesystem and initial template work
        # happens off the event loop. No user string becomes Jinja template source.
        await hass.async_add_executor_job(
            lambda: transform_html(
                original.render(theme_color="#03a9f4", extra_modules=(), extra_js_es5=()), branding
            )
        )
        login = await prepare_login_hook(hass, branding)
    except (OSError, ValueError) as err:
        raise ConfigEntryError(f"Branding was not applied: {err}") from err
    if view._template_cache is not original:
        raise ConfigEntryError(
            "Another component changed the index template during setup; branding was not applied"
        )
    branded = BrandedTemplate(original, branding)
    if login is not None:
        login.install()
    # Compatibility-sensitive hook: HA 2026.10.4 reads this cache directly.
    # Do not override IndexView methods, change routes, or clear global caches.
    view._template_cache = branded
    hass.data[DOMAIN] = Runtime(view, original, branded, login)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Restore only the template we own, preserving any later third-party hook."""
    if (runtime := hass.data.pop(DOMAIN, None)) is not None:
        if runtime.login is not None:
            runtime.login.restore()
        if runtime.view._template_cache is runtime.branded:
            runtime.view._template_cache = runtime.original
        else:
            _LOGGER.warning(
                "Another component replaced the index template; restart Core to finish cleanup"
            )
    return True
