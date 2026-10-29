"""Read and re-encode bounded local PNGs without URLs or upload endpoints."""

import base64
import io
import os
import re
import stat
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .const import ASSET_DIRECTORY

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 2048
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\.png", re.ASCII)


class AssetError(ValueError):
    """A requested branding image is missing or invalid."""


def sanitize_png(data: bytes) -> bytes:
    """Decode and re-encode a static PNG, discarding all original metadata.

    Pillow is already a Home Assistant Core dependency. Dimensions are checked
    before decoding. The output contains pixels from a fresh image, with no
    copied EXIF, text, animation, embedded profiles or trailing payloads.
    """
    if len(data) > MAX_FILE_BYTES or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssetError("Use a PNG file no larger than 2 MiB")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                raise AssetError("Use a static PNG image")
            if not all(1 <= dimension <= MAX_DIMENSION for dimension in image.size):
                raise AssetError("PNG dimensions must be between 1 and 2048 pixels")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            rgba = image.convert("RGBA")
            clean = Image.frombytes("RGBA", rgba.size, rgba.tobytes())
        output = io.BytesIO()
        clean.save(output, format="PNG")
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
    ) as err:
        if isinstance(err, AssetError):
            raise
        raise AssetError("The PNG image is damaged or unsupported") from err
    result = output.getvalue()
    if len(result) > MAX_FILE_BYTES:
        raise AssetError("The decoded PNG is too large; use a smaller logo")
    return result


def read_asset(config_directory: str, filename: str) -> str | None:
    """Read a basename from a dedicated directory; reject URLs and symlinks."""
    if filename == "":
        return None
    if not isinstance(filename, str) or not FILENAME.fullmatch(filename):
        raise AssetError("Enter a simple PNG filename, not a path or URL")
    config = Path(config_directory).resolve()
    root = config / ASSET_DIRECTORY
    if root.is_symlink() or not root.is_dir():
        raise AssetError(
            "Create the ha_rebrand_local directory inside your HA configuration directory"
        )
    try:
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise AssetError("Logo must be a regular file")
                data = stream.read(MAX_FILE_BYTES + 1)
        finally:
            os.close(directory_fd)
    except OSError as err:
        raise AssetError("Cannot read the PNG file from ha_rebrand_local") from err
    sanitized = sanitize_png(data)
    return "data:image/png;base64," + base64.b64encode(sanitized).decode("ascii")
