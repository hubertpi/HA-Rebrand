"""Verify local file boundaries, image decoding and metadata removal."""

import base64
import io

import pytest
from PIL import Image, PngImagePlugin

from custom_components.ha_rebrand_local.assets import (
    MAX_FILE_BYTES,
    AssetError,
    read_asset,
    sanitize_png,
)


def test_valid_png(png, tmp_path):
    directory = tmp_path / "ha_rebrand_local"
    directory.mkdir()
    (directory / "logo.png").write_bytes(png)
    value = read_asset(str(tmp_path), "logo.png")
    assert value.startswith("data:image/png;base64,")
    image = Image.open(io.BytesIO(base64.b64decode(value.split(",")[1])))
    assert image.size == (8, 8)


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.png",
        "/config/secret.png",
        "https://evil.invalid/logo.png",
        "//evil.invalid/a.png",
        "a.svg",
        "a.png?x=1",
        "a.png\x00",
        ".hidden.png",
        "a\\b.png",
    ],
)
def test_paths_and_urls_rejected(tmp_path, filename):
    with pytest.raises(AssetError):
        read_asset(str(tmp_path), filename)


def test_file_and_directory_symlinks_rejected(tmp_path, png):
    outside = tmp_path / "outside.png"
    outside.write_bytes(png)
    directory = tmp_path / "ha_rebrand_local"
    directory.mkdir()
    (directory / "logo.png").symlink_to(outside)
    with pytest.raises(AssetError):
        read_asset(str(tmp_path), "logo.png")
    (directory / "logo.png").unlink()
    directory.rmdir()
    directory.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(AssetError):
        read_asset(str(tmp_path), "outside.png")


@pytest.mark.parametrize(
    "data",
    [
        b'<svg onload="alert(1)"></svg>',
        b"not an image",
        b"\x89PNG\r\n\x1a\n",
        b"x" * (MAX_FILE_BYTES + 1),
    ],
)
def test_invalid_or_oversized_images_rejected(data):
    with pytest.raises(AssetError):
        sanitize_png(data)


def test_png_metadata_and_trailing_payload_removed():
    info = PngImagePlugin.PngInfo()
    info.add_text("comment", "<script>payload</script>")
    output = io.BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG", pnginfo=info)
    sanitized = sanitize_png(output.getvalue() + b"EXTRA_PAYLOAD")
    assert b"payload" not in sanitized
    assert b"EXTRA_PAYLOAD" not in sanitized
    assert Image.open(io.BytesIO(sanitized)).info == {}


def test_dimensions_rejected_before_decode():
    output = io.BytesIO()
    Image.new("RGB", (2049, 1)).save(output, format="PNG")
    with pytest.raises(AssetError):
        sanitize_png(output.getvalue())


def test_animation_rejected():
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(
        output, format="PNG", save_all=True, append_images=[Image.new("RGB", (2, 2), "blue")]
    )
    with pytest.raises(AssetError):
        sanitize_png(output.getvalue())


def test_missing_asset_rejected(tmp_path):
    (tmp_path / "ha_rebrand_local").mkdir()
    with pytest.raises(AssetError):
        read_asset(str(tmp_path), "missing.png")


def test_blank_logo_needs_no_directory(tmp_path):
    assert read_asset(str(tmp_path), "") is None
