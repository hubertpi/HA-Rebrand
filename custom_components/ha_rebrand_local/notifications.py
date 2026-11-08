"""Suppress default secondary artwork in Home Assistant HTML5 notifications."""

import inspect
import logging
from functools import wraps

from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import async_get_integration

from .mobile import MobileAssets

_LOGGER = logging.getLogger(__name__)


class NotificationBranding:
    """Hide secondary defaults and use the favicon for status-bar branding."""

    def __init__(self, hass, assets: MobileAssets):
        self.hass = hass
        self.defaults = {"icon": assets.notification_icon_url}
        if assets.notification_badge_url:
            self.defaults["badge"] = assets.notification_badge_url
        self.active = True
        self.unsubscribe = None
        self.module = None
        self.original_defaults = {}
        self.entity_class = None
        self.original_webpush = None
        self.wrapper = None

    async def start(self):
        if not self.active or not self.defaults["icon"]:
            return
        if "html5" in self.hass.config.components:
            await self._install()
        else:
            self.unsubscribe = self.hass.bus.async_listen(
                EVENT_COMPONENT_LOADED, self._component_loaded
            )

    async def _component_loaded(self, event):
        if event.data.get("component") != "html5":
            return
        if self.unsubscribe is not None:
            self.unsubscribe()
            self.unsubscribe = None
        await self._install()

    async def _install(self):
        try:
            integration = await async_get_integration(self.hass, "html5")
            module = await integration.async_get_platform("notify")
            if not self.active or self.module is not None:
                return
            original_defaults = {
                key: getattr(module, f"DEFAULT_{key.upper()}") for key in self.defaults
            }
            entity_class = module.HTML5NotifyEntity
            original_webpush = entity_class._webpush
            if not inspect.iscoroutinefunction(original_webpush) or not any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in inspect.signature(original_webpush).parameters.values()
            ):
                raise TypeError("Unfamiliar HTML5 notification helper")
        except ImportError, AttributeError, TypeError, HomeAssistantError:
            _LOGGER.exception("HTML5 notification branding could not be installed")
            return

        @wraps(original_webpush)
        async def branded_webpush(entity, *args, **kwargs):
            if self.active and entity.hass is self.hass and not kwargs.get("dismiss"):
                for key, value in self.defaults.items():
                    kwargs.setdefault(key, value)
            return await original_webpush(entity, *args, **kwargs)

        # Legacy notify.html5_* and notify.send_message read these constants
        # when building each payload. Explicit per-notification values win.
        self.module = module
        self.original_defaults = original_defaults
        self.entity_class = entity_class
        self.original_webpush = original_webpush
        self.wrapper = branded_webpush
        for key, value in self.defaults.items():
            setattr(module, f"DEFAULT_{key.upper()}", value)
        # html5.send_message can omit artwork entirely, so fill only missing
        # keyword arguments immediately before HA builds its own push payload.
        entity_class._webpush = branded_webpush

    def restore(self):
        if not self.active:
            return
        self.active = False
        if self.unsubscribe is not None:
            self.unsubscribe()
            self.unsubscribe = None
        if self.module is None:
            return
        for key, value in self.defaults.items():
            name = f"DEFAULT_{key.upper()}"
            if getattr(self.module, name) == value:
                setattr(self.module, name, self.original_defaults[key])
            else:
                _LOGGER.warning("Another component changed HTML5 %s; leaving it intact", key)
        if self.entity_class._webpush is self.wrapper:
            self.entity_class._webpush = self.original_webpush
        else:
            _LOGGER.warning("Another component wrapped HTML5 notifications; leaving it intact")
