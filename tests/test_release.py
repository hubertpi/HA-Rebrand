"""Verify release metadata, version safety, notes boundaries and native icons."""

import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.release_info import release_info

ROOT = Path(__file__).resolve().parents[1]


def write_metadata(root, version, changelog):
    folder = root / "custom_components/ha_rebrand_local"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps({"version": version}))
    (root / "CHANGELOG.md").write_text(changelog)


def test_current_release_has_notes():
    version, notes = release_info(ROOT)
    assert (
        version
        == json.loads((ROOT / "custom_components/ha_rebrand_local/manifest.json").read_text())[
            "version"
        ]
    )
    assert notes.strip()


@pytest.mark.parametrize("version", ["main", "0.1.2\ntag=wrong", "$(echo unsafe)"])
def test_unsafe_version_cannot_enter_action_outputs(tmp_path, version):
    write_metadata(tmp_path, version, "# Changelog\n")
    with pytest.raises(ValueError, match="major.minor.patch"):
        release_info(tmp_path)


@pytest.mark.parametrize(
    "notes", ["# Changelog\n## 0.1.1\nOld release\n", "# Changelog\n## 0.1.2\n\n"]
)
def test_release_requires_matching_nonempty_notes(tmp_path, notes):
    write_metadata(tmp_path, "0.1.2", notes)
    with pytest.raises(ValueError, match="changelog"):
        release_info(tmp_path)


def test_release_notes_exclude_other_versions(tmp_path):
    write_metadata(
        tmp_path, "0.1.2", "# Changelog\n\n## 0.1.2\n\n- New icon.\n\n## 0.1.1\n\n- Old layout.\n"
    )
    assert release_info(tmp_path) == ("0.1.2", "- New icon.\n")


@pytest.mark.parametrize(("filename", "size"), [("icon.png", 256), ("icon@2x.png", 512)])
def test_native_brand_images_are_valid_pngs(filename, size):
    path = ROOT / "custom_components/ha_rebrand_local/brand" / filename
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.size == (size, size)
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema() == (0, 255)
