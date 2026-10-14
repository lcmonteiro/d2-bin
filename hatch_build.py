"""Hatch build hook: put the official D2 binary (and its license) into the d2-bin wheel.

Every wheel build downloads the pinned D2 release for the target platform,
checks its SHA-256 against ``src/d2_bin/d2_release.json``, and ships
``d2_bin/bin/d2`` (``d2.exe`` on Windows) plus ``d2_bin/bin/D2-LICENSE.txt``.
The wheel is tagged for that platform; there is nothing to compile.

Environment:
- ``D2_BIN_PLATFORM=<linux|macos|windows>-<amd64|arm64>``: build for another
  platform (the release workflow builds all six from one runner).
- ``D2_BIN_CACHE``: where downloaded archives are kept (default: the user cache folder).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import shutil
import sysconfig
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent
RELEASE_FILE = ROOT / "src" / "d2_bin" / "d2_release.json"
EDITABLE_BIN = ROOT / "src" / "d2_bin" / "bin"
LICENSE_NAME = "D2-LICENSE.txt"

# Wheel platform tags for cross-builds. D2 is a static Go binary, so the oldest common baselines work.
WHEEL_TAGS = {
    "linux-amd64": "manylinux2014_x86_64.musllinux_1_1_x86_64",
    "linux-arm64": "manylinux2014_aarch64.musllinux_1_1_aarch64",
    "macos-amd64": "macosx_10_12_x86_64",
    "macos-arm64": "macosx_11_0_arm64",
    "windows-amd64": "win_amd64",
    "windows-arm64": "win_arm64",
}


def host_platform() -> str:
    system = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(platform.system())
    machine = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if system is None or machine is None:
        raise RuntimeError(f"D2 publishes no build for {platform.system()} {platform.machine()}")
    return f"{system}-{machine}"


def cache_dir() -> Path:
    if os.environ.get("D2_BIN_CACHE"):
        return Path(os.environ["D2_BIN_CACHE"])
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "d2-bin"


def fetch_archive(release: dict, target: str) -> bytes:
    """The release archive for ``target``, from the cache or GitHub, verified against the pinned hash."""
    expected = release["sha256"].get(target)
    if expected is None:
        raise RuntimeError(f"no pinned D2 build for platform '{target}' (known: {', '.join(release['sha256'])})")
    name = f"d2-{release['version']}-{target}.tar.gz"
    cached = cache_dir() / name
    if cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == expected:
        return cached.read_bytes()

    url = release["url"].format(version=release["version"], platform=target)
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
    except OSError as exc:
        raise RuntimeError(f"could not download D2 from {url}: {exc}") from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise RuntimeError(f"D2 archive {name} has SHA-256 {actual}, expected {expected}; refusing to package it")
    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    except OSError:
        pass  # the cache is only an optimisation
    return data


def _member(tar: tarfile.TarFile, suffix: str) -> tarfile.TarInfo:
    """The archive member ending in ``suffix``, skipping macOS AppleDouble (``._*``) entries."""
    for member in tar.getmembers():
        if member.isfile() and member.name.endswith(suffix) and "/._" not in member.name:
            return member
    raise RuntimeError(f"{suffix.lstrip('/')} not found in the D2 archive")


def extract(archive: bytes, target: str, dest: Path) -> list[Path]:
    """Write the d2 binary and D2's license into ``dest``; return both paths."""
    exe = "d2.exe" if target.startswith("windows") else "d2"
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for suffix, name in ((f"/bin/{exe}", exe), ("/LICENSE.txt", LICENSE_NAME)):
            source = tar.extractfile(_member(tar, suffix))
            path = dest / name
            with open(path, "wb") as out:
                shutil.copyfileobj(source, out)
            written.append(path)
    written[0].chmod(0o755)
    return written


class D2BundleHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel":
            return
        release = json.loads(RELEASE_FILE.read_text(encoding="utf-8"))
        cross = os.environ.get("D2_BIN_PLATFORM")
        target = cross or host_platform()
        archive = fetch_archive(release, target)

        if version == "editable":
            # Editable installs import from src/, so place the files there (git-ignored).
            extract(archive, target, EDITABLE_BIN)
            return

        staging = Path(tempfile.mkdtemp(prefix="d2-bin-"))
        for path in extract(archive, target, staging):
            build_data["force_include"][str(path)] = f"d2_bin/bin/{path.name}"
        build_data["pure_python"] = False
        plat = WHEEL_TAGS[target] if cross else sysconfig.get_platform().replace("-", "_").replace(".", "_")
        build_data["tag"] = f"py3-none-{plat}"
