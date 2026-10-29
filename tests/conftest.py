"""Test against the actual pinned HA frontend package and Core IndexView."""

import asyncio
import io
import sys
from copy import deepcopy
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import hass_frontend
import pytest
from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import KEY_HASS
from homeassistant.components.http.server import _serve_file
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def png():
    output = io.BytesIO()
    Image.new("RGBA", (8, 8), (20, 100, 200, 255)).save(output, format="PNG")
    return output.getvalue()


def make_harness(tmp_path, monkeypatch, real_login=False):
    app = web.Application()
    monkeypatch.setattr(
        frontend, "MANIFEST_JSON", frontend.Manifest(deepcopy(frontend.MANIFEST_JSON.manifest))
    )

    async def executor(function, *args):
        return await asyncio.to_thread(function, *args)

    hass = SimpleNamespace(
        data={
            frontend.DATA_PANELS: {"lovelace": object()},
            frontend.DATA_EXTRA_MODULE_URL: SimpleNamespace(urls=frozenset()),
            frontend.DATA_EXTRA_JS_URL_ES5: SimpleNamespace(urls=frozenset()),
        },
        config=SimpleNamespace(config_dir=str(tmp_path), safe_mode=False),
        async_add_executor_job=executor,
        http=SimpleNamespace(app=app),
    )
    app[KEY_HASS] = hass
    # HA keeps its production router open for dynamic view registration. This
    # isolated frozen-router harness registers the public icon view up front.
    from custom_components.ha_rebrand_local.mobile import ICON_PATH, VIEW_REGISTERED, IconView

    icon_view = IconView(hass)

    async def icon(request):
        return await icon_view.get(request, request.match_info["filename"])

    app.router.add_get(ICON_PATH + "{filename}", icon)

    async def manifest(request):
        return frontend.ManifestJSONView().get(request)

    app.router.add_get("/manifest.json", manifest)
    hass.data[VIEW_REGISTERED] = True
    view = frontend.IndexView(None, hass)

    async def authorize(request):
        return web.Response(text="original authorization route")

    if real_login:
        app.router.add_route(
            "GET",
            "/auth/authorize",
            partial(_serve_file, str(hass_frontend.where() / "authorize.html")),
        )
    else:
        app.router.add_get("/auth/authorize", authorize)
    app.router.register_resource(view)
    monkeypatch.setattr(frontend.onboarding, "async_is_onboarded", lambda _: True)
    return hass, view, app


@pytest.fixture
def harness(tmp_path, monkeypatch):
    return make_harness(tmp_path, monkeypatch)


@pytest.fixture
def login_harness(tmp_path, monkeypatch):
    return make_harness(tmp_path, monkeypatch, real_login=True)
