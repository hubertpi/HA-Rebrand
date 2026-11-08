"""Exercise real HA notification payload builders with outbound push mocked."""

import asyncio
import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.components.html5 import notify as html5
from PIL import Image, ImageDraw

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry
from custom_components.ha_rebrand_local.branding import Branding
from custom_components.ha_rebrand_local.const import DOMAIN
from custom_components.ha_rebrand_local.mobile import prepare_mobile_assets
from custom_components.ha_rebrand_local.notifications import NotificationBranding


@pytest.fixture
def artwork():
    image = Image.new("RGBA", (64, 64))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 51, 51), fill="red")
    draw.rectangle((24, 24, 39, 39), fill=(0, 0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    data = output.getvalue()
    branding = Branding(
        "Facility", True, None, None, "data:image/png;base64," + base64.b64encode(data).decode()
    )
    return data, prepare_mobile_assets(branding)


@pytest.fixture
async def hook(monkeypatch, artwork):
    hass = SimpleNamespace(config=SimpleNamespace(components={"html5"}))
    integration = SimpleNamespace(async_get_platform=AsyncMock(return_value=html5))
    monkeypatch.setattr(
        "custom_components.ha_rebrand_local.notifications.async_get_integration",
        AsyncMock(return_value=integration),
    )
    instance = NotificationBranding(hass, artwork[1])
    yield instance
    instance.restore()


def read_icon(assets, url):
    return Image.open(io.BytesIO(assets.files[url.rsplit("/", 1)[-1]])).convert("RGBA")


def test_transparent_badge_is_white_and_keeps_cutouts(artwork):
    assets = artwork[1]
    badge = read_icon(assets, assets.notification_badge_url)
    assert badge.size == (96, 96)
    assert badge.getpixel((0, 0))[3] == 0
    assert badge.getpixel((48, 48))[3] == 0
    assert badge.getpixel((30, 30)) == (255, 255, 255, 255)


@pytest.mark.parametrize("background,foreground", [("#20313b", "white"), ("white", "black")])
def test_opaque_flat_background_becomes_transparent(background, foreground):
    image = Image.new("RGBA", (64, 64), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 51, 51), fill=foreground)
    draw.rectangle((24, 24, 39, 39), fill=background)
    output = io.BytesIO()
    image.save(output, format="PNG")
    branding = Branding(
        "Facility",
        True,
        None,
        None,
        "data:image/png;base64," + base64.b64encode(output.getvalue()).decode(),
    )
    assets = prepare_mobile_assets(branding)
    badge = read_icon(assets, assets.notification_badge_url)
    assert badge.getpixel((0, 0))[3] == 0
    assert badge.getpixel((48, 48))[3] == 0
    assert badge.getpixel((30, 30)) == (255, 255, 255, 255)


async def test_legacy_notification_defaults_and_explicit_overrides(hook, monkeypatch):
    service = object.__new__(html5.HTML5NotificationService)
    service.hass = hook.hass
    service._push_message = AsyncMock()
    monkeypatch.setattr(html5, "deprecated_notify_action_call", lambda *args: None)
    original_icon = html5.DEFAULT_ICON
    await hook.start()
    data = {"image": "/local/snapshot.jpg", "url": "/dashboard/camera", "ttl": 0}
    await service.async_send_message("Doorbell", title="Shipping", data=data)
    payload = service._push_message.await_args.args[0]
    assert payload["icon"] == original_icon
    assert html5.DEFAULT_ICON == original_icon
    assert payload["badge"] == hook.defaults["badge"]
    assert payload["body"] == "Doorbell"
    assert payload["image"] == data["image"]
    assert payload["data"]["url"] == data["url"]
    assert data == {"image": "/local/snapshot.jpg", "url": "/dashboard/camera", "ttl": 0}
    await service.async_send_message(
        "Custom", data={"icon": "/custom.png", "badge": "", "url": "/other"}
    )
    payload = service._push_message.await_args.args[0]
    assert payload["icon"] == "/custom.png"
    assert payload["badge"] == ""


def make_entity(hass):
    entity = object.__new__(html5.HTML5NotifyEntity)
    entity.hass = hass
    entity.target = "test-browser"
    entity.registration = {
        "subscription": {"endpoint": "https://push.example.test/send", "keys": {"auth": "test"}}
    }
    entity.config_entry = SimpleNamespace(
        data={"vapid_email": "test@example.test", "vapid_prv_key": "test"}
    )
    entity.session = object()
    entity._async_record_notification = Mock()
    return entity


async def test_native_actions_defaults_explicit_values_and_dismiss(hook, monkeypatch):
    push = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None))
    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    original_icon = html5.DEFAULT_ICON
    await hook.start()
    entity = make_entity(hook.hass)
    await entity.async_send_message("Generic notification", "Title")
    payload = json.loads(push.await_args.args[1])
    assert payload["icon"] == original_icon
    assert html5.DEFAULT_ICON == original_icon
    assert payload["badge"] == hook.defaults["badge"]
    assert payload["body"] == "Generic notification"
    await entity.send_push_notification(
        message="Doorbell", title="Shipping", data={"url": "/camera"}, image="/snapshot.jpg"
    )
    payload = json.loads(push.await_args.args[1])
    assert "icon" not in payload
    assert payload["badge"] == hook.defaults["badge"]
    assert payload["data"] == {"url": "/camera", "jwt": "test-jwt"}
    assert payload["image"] == "/snapshot.jpg"
    await entity.send_push_notification(message="Override", icon="/own.png", badge="")
    payload = json.loads(push.await_args.args[1])
    assert payload["icon"] == "/own.png"
    assert payload["badge"] == ""
    await entity.dismiss_notification("doorbell")
    payload = json.loads(push.await_args.args[1])
    assert payload["dismiss"] is True
    assert "badge" not in payload
    assert "icon" not in payload


async def test_exact_restore_and_no_wrappers_after_repeated_reload(hook):
    original = html5.HTML5NotifyEntity._webpush
    defaults = html5.DEFAULT_ICON, html5.DEFAULT_BADGE
    for _ in range(3):
        instance = NotificationBranding(
            hook.hass,
            SimpleNamespace(notification_badge_url="/badge.png"),
        )
        await instance.start()
        assert html5.HTML5NotifyEntity._webpush is not original
        instance.restore()
        assert html5.HTML5NotifyEntity._webpush is original
        assert (html5.DEFAULT_ICON, html5.DEFAULT_BADGE) == defaults


async def test_later_owner_is_preserved_and_retained_wrapper_is_inactive(hook, monkeypatch):
    captured = AsyncMock()
    monkeypatch.setattr(html5.HTML5NotifyEntity, "_webpush", captured)
    await hook.start()
    wrapper = html5.HTML5NotifyEntity._webpush

    async def later_owner(entity, *args, **kwargs):
        return await wrapper(entity, *args, **kwargs)

    monkeypatch.setattr(html5.HTML5NotifyEntity, "_webpush", later_owner)
    monkeypatch.setattr(html5, "DEFAULT_BADGE", "/later.png")
    hook.restore()
    assert html5.DEFAULT_BADGE == "/later.png"
    assert html5.HTML5NotifyEntity._webpush is later_owner
    await later_owner(SimpleNamespace(hass=hook.hass), message="After unload")
    assert captured.await_args.kwargs == {"message": "After unload"}


async def test_late_html5_setup_and_unload_cancel_listener(hook):
    hook.hass.config.components.clear()
    unsubscribe = Mock()
    hook.hass.bus = SimpleNamespace(async_listen=Mock(return_value=unsubscribe))
    await hook.start()
    assert hook.module is None
    callback = hook.hass.bus.async_listen.call_args.args[1]
    await callback(SimpleNamespace(data={"component": "other"}))
    assert hook.module is None
    await callback(SimpleNamespace(data={"component": "html5"}))
    unsubscribe.assert_called_once()
    assert hook.module is html5
    hook.restore()
    second = NotificationBranding(
        hook.hass,
        SimpleNamespace(notification_badge_url="/badge.png"),
    )
    await second.start()
    second.restore()
    assert unsubscribe.call_count == 2


async def test_unload_during_platform_import_cannot_install_afterwards(hook, monkeypatch):
    started = asyncio.Event()
    proceed = asyncio.Event()

    async def load_platform(_):
        started.set()
        await proceed.wait()
        return html5

    integration = SimpleNamespace(async_get_platform=load_platform)
    monkeypatch.setattr(
        "custom_components.ha_rebrand_local.notifications.async_get_integration",
        AsyncMock(return_value=integration),
    )
    original = html5.HTML5NotifyEntity._webpush
    task = asyncio.create_task(hook.start())
    await started.wait()
    hook.restore()
    proceed.set()
    await task
    assert hook.module is None
    assert html5.HTML5NotifyEntity._webpush is original


async def test_real_setup_and_unload_serve_then_remove_notification_artwork(
    login_harness, artwork, tmp_path
):
    hass, _, _ = login_harness
    directory = tmp_path / "ha_rebrand_local"
    directory.mkdir()
    (directory / "icon.png").write_bytes(artwork[0])
    entry = SimpleNamespace(options={"favicon": "icon.png"})
    await async_setup_entry(hass, entry)
    runtime = hass.data[DOMAIN]
    assert runtime.notifications.defaults["badge"] == runtime.mobile.notification_badge_url
    async with TestClient(TestServer(hass.http.app)) as client:
        for path in runtime.notifications.defaults.values():
            response = await client.get(path)
            assert response.status == 200
            assert response.content_type == "image/png"
        await async_unload_entry(hass, entry)
        assert (await client.get(runtime.mobile.notification_badge_url)).status == 404
    assert not runtime.notifications.active
    assert DOMAIN not in hass.data


async def test_no_artwork_does_not_load_html5_or_attach_a_listener(hook):
    instance = NotificationBranding(
        SimpleNamespace(),
        SimpleNamespace(notification_badge_url=None),
    )
    await instance.start()
    assert instance.module is None
    assert instance.unsubscribe is None


@pytest.mark.parametrize("error", [RuntimeError("Setup failed"), asyncio.CancelledError()])
async def test_setup_failure_or_cancellation_restores_already_installed_branding(
    login_harness, monkeypatch, error
):
    from homeassistant.components import frontend

    hass, view, _ = login_harness
    original = view.get_template()
    name = frontend.MANIFEST_JSON["name"]
    monkeypatch.setattr(NotificationBranding, "start", AsyncMock(side_effect=error))
    with pytest.raises(type(error)):
        await async_setup_entry(hass, SimpleNamespace(options={"brand_name": "Facility"}))
    assert DOMAIN not in hass.data
    assert view._template_cache is original
    assert frontend.MANIFEST_JSON["name"] == name


async def test_unfamiliar_html5_helper_leaves_all_defaults_intact(hook, monkeypatch, caplog):
    original_icon, original_badge = html5.DEFAULT_ICON, html5.DEFAULT_BADGE
    monkeypatch.setattr(html5.HTML5NotifyEntity, "_webpush", None)
    await hook.start()
    assert hook.module is None
    assert html5.DEFAULT_ICON == original_icon
    assert html5.DEFAULT_BADGE == original_badge
    assert html5.HTML5NotifyEntity._webpush is None
    assert "could not be installed" in caplog.text
