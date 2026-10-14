"""The installed package: binary, version, license and the d2 command."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import d2_bin

ROOT = Path(__file__).resolve().parents[1]


def test_executable_is_bundled_and_runnable():
    path = Path(d2_bin.executable())
    assert path.is_file() and path.name in ("d2", "d2.exe")
    assert os.access(path, os.X_OK)


def test_bundled_binary_is_the_pinned_release():
    out = d2_bin.run("--version", capture_output=True, text=True).stdout.strip()
    assert out == d2_bin.D2_VERSION


def test_package_version_follows_d2():
    pyproject = (ROOT / "pyproject.toml").read_text()
    version = re.search(r'(?m)^version = "([^"]+)"$', pyproject).group(1)
    assert version.split(".post")[0] == d2_bin.D2_VERSION.lstrip("v")


def test_d2_license_is_shipped():
    license_file = Path(d2_bin.executable()).parent / "D2-LICENSE.txt"
    assert "Mozilla Public License Version 2.0" in license_file.read_text()


def test_render_svg(tmp_path):
    source = tmp_path / "flow.d2"
    source.write_text('user -> api: "POST /reset {email}"\n')
    d2_bin.run(str(source), str(tmp_path / "flow.svg"), "--theme=0", capture_output=True)
    assert "</svg>" in (tmp_path / "flow.svg").read_text()


def test_python_m_d2_bin_passes_args_and_exit_code(tmp_path):
    version = subprocess.run([sys.executable, "-m", "d2_bin", "--version"], capture_output=True, text=True)
    assert version.returncode == 0 and version.stdout.strip() == d2_bin.D2_VERSION
    broken = tmp_path / "broken.d2"
    broken.write_text("a -> {\n")
    failed = subprocess.run([sys.executable, "-m", "d2_bin", str(broken), str(tmp_path / "x.svg")], capture_output=True, text=True)
    assert failed.returncode != 0


def test_missing_binary_message(monkeypatch, tmp_path):
    monkeypatch.setattr(d2_bin.resources, "files", lambda _: tmp_path)
    with pytest.raises(FileNotFoundError, match="reinstall d2-bin"):
        d2_bin.executable()


def test_pinned_release_covers_six_platforms():
    release = json.loads((ROOT / "src/d2_bin/d2_release.json").read_text())
    assert sorted(release["sha256"]) == sorted(
        f"{os}-{arch}" for os in ("linux", "macos", "windows") for arch in ("amd64", "arm64")
    )
