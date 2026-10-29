"""Test HTML security and rendering using the shipped frontend HTML."""

import json
import re
from pathlib import Path

import hass_frontend
import jinja2
import pytest

from custom_components.ha_rebrand_local.branding import (
    BrandedTemplate,
    Branding,
    CompatibilityError,
    load_branding,
    transform_html,
)


@pytest.fixture
def original():
    return jinja2.Template((hass_frontend.where() / "index.html").read_text())


@pytest.fixture
def html(original):
    return original.render(theme_color="#abcdef", extra_modules=(), extra_js_es5=())


def brand(**changes):
    values = {
        "name": "Facility Control",
        "hide_foundation": True,
        "light": None,
        "dark": None,
        "favicon": None,
    }
    return Branding(**{**values, **changes})


def test_real_template_markers(html):
    result = transform_html(html, brand())
    assert "<title>Facility Control</title>" in result
    assert 'id="ha-rebrand-local-name">Facility Control</span>' in result
    assert "#ha-launch-screen .ohf-logo{visibility:hidden!important;}" in result
    assert "<home-assistant" in result
    assert "/static/images/home-assistant-logo-loading.svg" in result


def test_defaults_and_foundation_toggle(html, tmp_path):
    result = transform_html(html, load_branding(str(tmp_path), {"hide_foundation": False}))
    assert "<title>Home Assistant</title>" in result
    assert "visibility:hidden" not in result
    assert 'id="ha-rebrand-local-name"' not in result
    assert 'id="ha-rebrand-local-title"' not in result


def test_light_dark_and_favicon(html):
    result = transform_html(
        html,
        brand(
            light="data:image/png;base64,LIGHT",
            dark="data:image/png;base64,DARK",
            favicon="data:image/png;base64,ICON",
        ),
    )
    assert 'src="data:image/png;base64,LIGHT"' in result
    assert 'srcset="data:image/png;base64,DARK"' in result
    assert 'href="data:image/png;base64,ICON"' in result
    assert 'rel="icon" href="/static/icons/favicon.ico"' not in result


def test_dark_only_used_for_both_modes(html):
    result = transform_html(html, brand(dark="data:image/png;base64,DARK"))
    assert 'src="data:image/png;base64,DARK"' in result


@pytest.mark.parametrize(
    "name",
    [
        "</title><script>alert(1)</script>",
        '</script><script src="https://evil.invalid/x.js"></script>',
        "{{ 7 * 7 }}",
        '{% include "secret" %}',
        "A & B \" C ' D",
    ],
)
def test_names_never_become_html_js_or_jinja(original, name):
    wrapped = BrandedTemplate(original, brand(name=name))
    result = wrapped.render(theme_color="#abcdef", extra_modules=(), extra_js_es5=())
    assert "<script>alert(1)</script>" not in result
    assert '<script src="https://evil.invalid' not in result
    script = re.search(r'<script id="ha-rebrand-local-title">(.*?)</script>', result).group(1)
    literal = script.split("const name=", 1)[1].split(";const title=", 1)[0]
    assert json.loads(literal) == name
    assert "</script>" not in literal
    if name.startswith("{{"):
        assert "{{ 7 * 7 }}" in result


@pytest.mark.parametrize(
    "replacement", ["ha-launch-screen", "home-assistant-logo-loading.svg", "ohf-logo"]
)
def test_changed_structure_is_rejected(html, replacement):
    with pytest.raises(CompatibilityError):
        transform_html(html.replace(replacement, "changed"), brand())


def test_runtime_failure_returns_original_and_logs_once(caplog):
    original = jinja2.Template("<html><head></head><body>changed</body></html>")
    wrapper = BrandedTemplate(original, brand())
    assert wrapper.render() == original.render()
    assert wrapper.render() == original.render()
    assert caplog.text.count("serving original HTML") == 1


def test_unrelated_modules_preserved(original):
    wrapped = BrandedTemplate(original, brand())
    result = wrapped.render(
        theme_color="#abcdef", extra_modules=("/local/example.js",), extra_js_es5=()
    )
    assert "/local/example.js" in result


@pytest.mark.parametrize("name", ["", " ", "x" * 81, "line\nbreak", "\u4e2d\u6587", "\u00e9"])
def test_english_printable_name_validation(tmp_path, name):
    with pytest.raises(ValueError):
        load_branding(str(tmp_path), {"brand_name": name})


def test_source_files_are_ascii():
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*"):
        if path.is_file() and not any(
            part.startswith(".") or part in {"__pycache__", "node_modules"}
            for part in path.relative_to(root).parts
        ):
            if path.suffix in {".py", ".md", ".json", ".yaml", ".yml", ".toml"}:
                path.read_text().encode("ascii")


@pytest.mark.parametrize("width", [95, 801, "320", True, 320.5, float("nan"), float("inf"), None])
def test_invalid_logo_width_is_rejected(tmp_path, width):
    from custom_components.ha_rebrand_local.branding import LogoWidthError

    with pytest.raises(LogoWidthError):
        load_branding(str(tmp_path), {"logo_width": width})


def test_existing_options_receive_larger_default_without_migration(tmp_path):
    branding = load_branding(str(tmp_path), {"brand_name": "Facility Control"})
    assert branding.logo_width == 320


def test_custom_logo_keeps_intrinsic_aspect_and_respects_selected_width(html):
    result = transform_html(html, brand(light="data:image/png;base64,LOGO", logo_width=480))
    assert "width:480px;height:auto;max-width:80vw;max-height:40vh;" in result
    image = re.search(
        r'<img class="ha-logo" src="data:image/png;base64,LOGO"[^>]*>', result
    ).group()
    assert 'height="96"' not in image
    assert 'width="96"' not in image
    assert "flex-direction:column;" in result
