"""Validate version metadata and extract this release's notes for GitHub Actions."""

import json
import re
from pathlib import Path


def release_info(root: Path) -> tuple[str, str]:
    """Require a numeric version and a matching nonempty changelog section."""
    manifest = json.loads((root / "custom_components/ha_rebrand_local/manifest.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Release versions must use major.minor.patch")
    changelog = (root / "CHANGELOG.md").read_text()
    match = re.search(
        rf"^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)",
        changelog,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None or not (notes := match.group(1).strip()):
        raise ValueError("Add a changelog section matching the manifest version")
    return version, notes + "\n"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    version, notes = release_info(root)
    (root / "release-notes.md").write_text(notes)
    print(f"version={version}")
    print(f"tag=v{version}")
