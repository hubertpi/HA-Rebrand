"""Test against the actual pinned HA frontend package and Core IndexView."""

import asyncio
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import KEY_HASS
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def png():
    output = io.BytesIO()
    Image.new("RGBA", (8, 8), (20, 100, 200, 255)).save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def harness(tmp_path, monkeypatch):
    app = web.Application()

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
    view = frontend.IndexView(None, hass)

    async def authorize(request):
        return web.Response(text="original authorization route")

    app.router.add_get("/auth/authorize", authorize)
    app.router.register_resource(view)
    monkeypatch.setattr(frontend.onboarding, "async_is_onboarded", lambda _: True)
    return hass, view, app
