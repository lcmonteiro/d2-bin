"""Move pyd2 to a new D2 release: pin the archive hashes and set the package version.

    python scripts/update_d2.py              # latest D2 release from GitHub
    python scripts/update_d2.py v0.7.2       # a given release

Downloads the six release archives, records their SHA-256 in
src/pyd2/d2_release.json and sets the version in pyproject.toml to the D2
version (v0.7.2 -> 0.7.2). Prints the new version, or nothing when already
pinned. Used weekly by .github/workflows/update.yml, which opens a PR.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILE = ROOT / "src" / "pyd2" / "d2_release.json"
PYPROJECT = ROOT / "pyproject.toml"
LATEST_API = "https://api.github.com/repos/terrastruct/d2/releases/latest"
VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "pyd2-updater"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def latest_version(get: Callable[[str], bytes] = _get) -> str:
    return json.loads(get(LATEST_API))["tag_name"]


def release_hashes(release: dict, version: str, get: Callable[[str], bytes] = _get) -> dict[str, str]:
    hashes = {}
    for platform in release["sha256"]:
        url = release["url"].format(version=version, platform=platform)
        hashes[platform] = hashlib.sha256(get(url)).hexdigest()
    return hashes


def apply(version: str, hashes: dict[str, str], release_file: Path = RELEASE_FILE, pyproject: Path = PYPROJECT) -> None:
    release = json.loads(release_file.read_text(encoding="utf-8"))
    release["version"] = version
    release["sha256"] = hashes
    release_file.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    text = pyproject.read_text(encoding="utf-8")
    new_text, count = re.subn(r'(?m)^version = "[^"]*"$', f'version = "{version.lstrip("v")}"', text, count=1)
    if count != 1:
        raise SystemExit(f"no version line in {pyproject}")
    pyproject.write_text(new_text, encoding="utf-8")


def update(version: str | None = None, get: Callable[[str], bytes] = _get, release_file: Path = RELEASE_FILE, pyproject: Path = PYPROJECT) -> str | None:
    """Pin ``version`` (default: latest); return it, or None when it is already pinned."""
    version = version or latest_version(get)
    if not VERSION_RE.match(version):
        raise SystemExit(f"unexpected D2 version '{version}' (expected vX.Y.Z)")
    release = json.loads(release_file.read_text(encoding="utf-8"))
    if release["version"] == version:
        return None
    apply(version, release_hashes(release, version, get), release_file, pyproject)
    return version


def main() -> None:
    version = update(sys.argv[1] if len(sys.argv) > 1 else None)
    if version:
        print(version)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                out.write(f"version={version}\n")


if __name__ == "__main__":
    main()
