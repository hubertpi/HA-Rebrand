"""Check secondary-icon suppression using HA's real HTML5 payload builders."""

import asyncio
import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientConnectionError
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.components.html5 import notify as html5
from homeassistant.exceptions import HomeAssistantError
from PIL import Image, ImageDraw

from custom_components.ha_rebrand_local import async_setup_entry, async_unload_entry
from custom_components.ha_rebrand_local.branding import Branding
from custom_components.ha_rebrand_local.const import DOMAIN
from custom_components.ha_rebrand_local.mobile import prepare_mobile_assets
from custom_components.ha_rebrand_local.notifications import NotificationBranding


@pytest.fixture
async def hook(monkeypatch):
    hass = SimpleNamespace(config=SimpleNamespace(components={"html5"}))
    assets = prepare_mobile_assets(Branding("Facility", True, None, None, None))
    integration = SimpleNamespace(async_get_platform=AsyncMock(return_value=html5))
    monkeypatch.setattr(
        "custom_components.ha_rebrand_local.notifications.async_get_integration",
        AsyncMock(return_value=integration),
    )
    instance = NotificationBranding(hass, assets)
    yield instance
    instance.restore()


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


@pytest.mark.parametrize("generic", [False, True])
async def test_native_default_icon_is_blank_but_badge_is_untouched(hook, monkeypatch, generic):
    push = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None))
    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    badge = html5.DEFAULT_BADGE
    await hook.start()
    entity = make_entity(hook.hass)
    if generic:
        await entity.async_send_message("Plain", "Test")
    else:
        await entity.send_push_notification(message="Plain", title="Test")
    payload = json.loads(push.await_args.args[1])
    assert payload["icon"] == hook.defaults["icon"]
    assert payload["body"] == "Plain"
    assert "image" not in payload
    assert html5.DEFAULT_BADGE == badge
    if generic:
        assert payload["badge"] == badge
    else:
        assert "badge" not in payload


async def test_explicit_picture_icon_badge_actions_and_click_url_survive(hook, monkeypatch):
    push = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None))
    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    await hook.start()
    entity = make_entity(hook.hass)
    await entity.send_push_notification(
        message="Doorbell",
        title="Shipping",
        image="/local/doorbell_snapshot.jpg",
        data={"url": "/dashboard/camera"},
        actions=[{"action": "open", "title": "Open"}],
    )
    payload = json.loads(push.await_args.args[1])
    assert payload["image"] == "/local/doorbell_snapshot.jpg"
    assert payload["icon"] == hook.defaults["icon"]
    assert payload["data"]["url"] == "/dashboard/camera"
    assert payload["actions"] == [{"action": "open", "title": "Open"}]
    await entity.send_push_notification(message="Override", icon="/custom.png", badge="/badge.png")
    payload = json.loads(push.await_args.args[1])
    assert payload["icon"] == "/custom.png"
    assert payload["badge"] == "/badge.png"
    await entity.dismiss_notification("doorbell")
    payload = json.loads(push.await_args.args[1])
    assert payload["dismiss"] is True
    assert "icon" not in payload


async def test_legacy_defaults_and_explicit_artwork(hook, monkeypatch):
    service = object.__new__(html5.HTML5NotificationService)
    service.hass = hook.hass
    service._push_message = AsyncMock()
    monkeypatch.setattr(html5, "deprecated_notify_action_call", lambda *args: None)
    badge = html5.DEFAULT_BADGE
    await hook.start()
    await service.async_send_message("Plain")
    payload = service._push_message.await_args.args[0]
    assert payload["icon"] == hook.defaults["icon"]
    assert payload["badge"] == badge
    await service.async_send_message(
        "Doorbell", data={"image": "/snapshot.jpg", "icon": "/custom.png", "badge": "/own.png"}
    )
    payload = service._push_message.await_args.args[0]
    assert payload["image"] == "/snapshot.jpg"
    assert payload["icon"] == "/custom.png"
    assert payload["badge"] == "/own.png"


async def test_blank_png_is_public_and_disappears_after_unload(login_harness):
    hass, _, app = login_harness
    entry = SimpleNamespace(options={})
    await async_setup_entry(hass, entry)
    url = hass.data[DOMAIN].mobile.notification_icon_url
    async with TestClient(TestServer(app)) as client:
        response = await client.get(url)
        assert response.status == 200
        assert response.content_type == "image/png"
        with Image.open(io.BytesIO(await response.read())) as image:
            assert image.size == (96, 96)
            assert image.getchannel("A").getextrema() == (0, 0)
        await async_unload_entry(hass, entry)
        assert (await client.get(url)).status == 404


async def test_late_html5_setup_and_unload_cancel_listener(hook):
    hook.hass.config.components.clear()
    unsubscribe = Mock()
    hook.hass.bus = SimpleNamespace(async_listen=Mock(return_value=unsubscribe))
    original = html5.DEFAULT_ICON
    await hook.start()
    assert html5.DEFAULT_ICON == original
    callback = hook.hass.bus.async_listen.call_args.args[1]
    await callback(SimpleNamespace(data={"component": "other"}))
    assert hook.module is None
    await callback(SimpleNamespace(data={"component": "html5"}))
    unsubscribe.assert_called_once()
    assert html5.DEFAULT_ICON == hook.defaults["icon"]
    hook.restore()
    assert html5.DEFAULT_ICON == original


async def test_unload_during_import_cannot_install_afterwards(hook, monkeypatch):
    started, proceed = asyncio.Event(), asyncio.Event()

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
    assert html5.HTML5NotifyEntity._webpush is original
    assert hook.module is None


async def test_repeated_reload_restores_defaults_and_preserves_badge(hook):
    original = html5.DEFAULT_ICON, html5.DEFAULT_BADGE, html5.HTML5NotifyEntity._webpush
    for _ in range(3):
        await hook.start()
        assert html5.DEFAULT_BADGE == original[1]
        hook.restore()
        assert (
            html5.DEFAULT_ICON,
            html5.DEFAULT_BADGE,
            html5.HTML5NotifyEntity._webpush,
        ) == original
        hook = NotificationBranding(
            hook.hass,
            SimpleNamespace(notification_icon_url="/blank.png", notification_badge_url=None),
        )


@pytest.mark.parametrize("route", ["html5", "generic", "legacy"])
async def test_favicon_badge_in_all_native_notification_paths(hook, monkeypatch, route):
    image = Image.new("RGBA", (64, 64))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 51, 51), fill="red")
    draw.rectangle((24, 24, 39, 39), fill=(0, 0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
    assets = prepare_mobile_assets(Branding("Facility", True, None, None, uri))
    instance = NotificationBranding(hook.hass, assets)
    push = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None))
    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    original = html5.DEFAULT_BADGE, html5.DEFAULT_ICON
    await instance.start()
    try:
        if route == "legacy":
            service = object.__new__(html5.HTML5NotificationService)
            service.hass = hook.hass
            service._push_message = AsyncMock()
            monkeypatch.setattr(html5, "deprecated_notify_action_call", lambda *args: None)
            await service.async_send_message("Plain")
            payload = service._push_message.await_args.args[0]
        else:
            entity = make_entity(hook.hass)
            if route == "generic":
                await entity.async_send_message("Plain", "Test")
            else:
                await entity.send_push_notification(message="Plain", title="Test")
            payload = json.loads(push.await_args.args[1])
        assert payload["badge"] == assets.notification_badge_url
        assert payload["icon"] == assets.notification_icon_url
        with Image.open(io.BytesIO(assets.files[payload["badge"].rsplit("/", 1)[1]])) as badge:
            assert badge.getpixel((0, 0))[3] == 0
            assert badge.getpixel((48, 48))[3] == 0
            assert badge.getpixel((30, 30)) == (255, 255, 255, 255)
    finally:
        instance.restore()
    assert (html5.DEFAULT_BADGE, html5.DEFAULT_ICON) == original


@pytest.mark.parametrize("background,foreground", [("#20313b", "white"), ("white", "black")])
def test_opaque_favicon_background_is_removed_from_status_bar_badge(background, foreground):
    image = Image.new("RGBA", (64, 64), background)
    ImageDraw.Draw(image).rectangle((12, 12, 51, 51), fill=foreground)
    output = io.BytesIO()
    image.save(output, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
    assets = prepare_mobile_assets(Branding("Facility", True, None, None, uri))
    with Image.open(
        io.BytesIO(assets.files[assets.notification_badge_url.rsplit("/", 1)[1]])
    ) as badge:
        assert badge.getpixel((0, 0))[3] == 0
        assert badge.getpixel((30, 30)) == (255, 255, 255, 255)


@pytest.mark.parametrize("error", [RuntimeError("Setup failed"), asyncio.CancelledError()])
async def test_failed_setup_restores_frontend_hooks(login_harness, monkeypatch, error):
    hass, view, _ = login_harness
    original = view.get_template()
    monkeypatch.setattr(NotificationBranding, "start", AsyncMock(side_effect=error))
    with pytest.raises(type(error)):
        await async_setup_entry(hass, SimpleNamespace(options={}))
    assert DOMAIN not in hass.data
    assert view._template_cache is original


async def test_unfamiliar_platform_does_not_change_defaults(hook, monkeypatch):
    original = html5.DEFAULT_ICON, html5.DEFAULT_BADGE
    monkeypatch.setattr(html5.HTML5NotifyEntity, "_webpush", None)
    await hook.start()
    assert (html5.DEFAULT_ICON, html5.DEFAULT_BADGE) == original
    assert hook.module is None


async def test_failed_native_push_does_not_disable_or_block_later_notifications(hook, monkeypatch):
    response = SimpleNamespace(raise_for_status=lambda: None)
    push = AsyncMock(side_effect=[ClientConnectionError("Simulated push failure"), response])
    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    await hook.start()
    entity = make_entity(hook.hass)
    with pytest.raises(HomeAssistantError):
        await entity.send_push_notification(message="First")
    async with asyncio.timeout(2):
        await entity.send_push_notification(message="Second")
    assert push.await_count == 2
    assert json.loads(push.await_args.args[1])["body"] == "Second"
    assert hook.active


async def test_concurrent_notifications_do_not_share_a_lock_or_mutate_image_urls(hook, monkeypatch):
    payloads = []
    active = peak = 0

    async def push(subscription, data, *args, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        payloads.append(json.loads(data))
        await asyncio.sleep(0)
        active -= 1
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    await hook.start()
    entity = make_entity(hook.hass)
    async with asyncio.timeout(3):
        await asyncio.gather(
            *(
                entity.send_push_notification(
                    message=f"Doorbell {i}", image=f"/local/doorbell_snapshot.jpg?v={i}"
                )
                for i in range(250)
            )
        )
    assert len(payloads) == 250
    assert peak > 1
    for i, payload in enumerate(payloads):
        assert payload["body"] == f"Doorbell {i}"
        assert payload["image"] == f"/local/doorbell_snapshot.jpg?v={i}"
        assert payload["icon"] == hook.defaults["icon"]


async def test_one_slow_push_does_not_hold_up_the_next(hook, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()

    async def push(subscription, data, *args, **kwargs):
        if json.loads(data)["body"] == "Slow":
            entered.set()
            await release.wait()
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(html5, "webpush_async", push)
    monkeypatch.setattr(html5, "add_jwt", lambda *args: "test-jwt")
    await hook.start()
    entity = make_entity(hook.hass)
    slow = asyncio.create_task(entity.send_push_notification(message="Slow"))
    try:
        async with asyncio.timeout(2):
            await entered.wait()
            await entity.send_push_notification(message="Next")
        assert not slow.done()
    finally:
        release.set()
        await slow
