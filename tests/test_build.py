"""The build hook (hatch_build.py) and the release updater (scripts/update_d2.py)."""

import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load("hatch_build", "hatch_build.py")
updater = load("update_d2", "scripts/update_d2.py")


def make_archive(exe="d2"):
    buf = io.BytesIO()
    entries = [
        (f"d2-v0/bin/._{exe}", b"apple junk"),
        (f"d2-v0/bin/{exe}", b"#!binary"),
        ("d2-v0/._LICENSE.txt", b"apple junk"),
        ("d2-v0/LICENSE.txt", b"Mozilla Public License Version 2.0"),
    ]
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, data in entries:
            info = tarfile.TarInfo(path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def release(monkeypatch, tmp_path):
    archive = make_archive()
    monkeypatch.setenv("PYD2_CACHE", str(tmp_path / "cache"))
    data = {"version": "v9.9.9", "url": "https://example.invalid/{version}/{platform}.tar.gz", "sha256": {"linux-amd64": hashlib.sha256(archive).hexdigest()}}
    return data, archive


def test_download_is_verified_and_cached(release, monkeypatch):
    data, archive = release
    calls = []
    monkeypatch.setattr(hook.urllib.request, "urlopen", lambda url, timeout: calls.append(url) or Response(archive))
    assert hook.fetch_archive(data, "linux-amd64") == archive
    assert hook.fetch_archive(data, "linux-amd64") == archive
    assert calls == ["https://example.invalid/v9.9.9/linux-amd64.tar.gz"]


def test_tampered_download_is_refused(release, monkeypatch):
    monkeypatch.setattr(hook.urllib.request, "urlopen", lambda url, timeout: Response(b"evil"))
    with pytest.raises(RuntimeError, match="refusing to package it"):
        hook.fetch_archive(release[0], "linux-amd64")


def test_unknown_platform(release):
    with pytest.raises(RuntimeError, match="no pinned D2 build for platform 'solaris-sparc'"):
        hook.fetch_archive(release[0], "solaris-sparc")


@pytest.mark.parametrize("target, exe", [("linux-amd64", "d2"), ("windows-arm64", "d2.exe")])
def test_extract_binary_and_license_skipping_apple_metadata(tmp_path, target, exe):
    binary, license_file = hook.extract(make_archive(exe), target, tmp_path)
    assert binary.name == exe and binary.read_bytes() == b"#!binary"
    assert license_file.name == "D2-LICENSE.txt" and b"Mozilla" in license_file.read_bytes()


@pytest.mark.parametrize(
    "system, machine, expected",
    [("Linux", "x86_64", "linux-amd64"), ("Linux", "aarch64", "linux-arm64"), ("Darwin", "arm64", "macos-arm64"), ("Windows", "AMD64", "windows-amd64")],
)
def test_host_platform(monkeypatch, system, machine, expected):
    monkeypatch.setattr(hook.platform, "system", lambda: system)
    monkeypatch.setattr(hook.platform, "machine", lambda: machine)
    assert hook.host_platform() == expected


def test_every_pinned_platform_has_a_wheel_tag():
    pinned = json.loads((ROOT / "src/pyd2/d2_release.json").read_text())
    assert set(pinned["sha256"]) == set(hook.WHEEL_TAGS)


# --- updater -----------------------------------------------------------------


@pytest.fixture
def files(tmp_path):
    release_file = tmp_path / "d2_release.json"
    release_file.write_text(json.dumps({"comment": "x", "version": "v0.7.1", "url": "https://dl/{version}/{platform}", "sha256": {"linux-amd64": "a", "macos-arm64": "b"}}))
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "pyd2"\nversion = "0.7.1.post1"\n')
    return release_file, pyproject


def fake_get(url):
    if url == updater.LATEST_API:
        return b'{"tag_name": "v0.8.0"}'
    return url.encode()


def test_update_pins_hashes_and_version(files):
    release_file, pyproject = files
    assert updater.update(get=fake_get, release_file=release_file, pyproject=pyproject) == "v0.8.0"
    data = json.loads(release_file.read_text())
    assert data["version"] == "v0.8.0" and data["comment"] == "x"
    assert data["sha256"] == {
        "linux-amd64": hashlib.sha256(b"https://dl/v0.8.0/linux-amd64").hexdigest(),
        "macos-arm64": hashlib.sha256(b"https://dl/v0.8.0/macos-arm64").hexdigest(),
    }
    assert 'version = "0.8.0"\n' in pyproject.read_text()


def test_update_is_a_no_op_when_pinned(files):
    release_file, pyproject = files
    before = release_file.read_text(), pyproject.read_text()
    assert updater.update("v0.7.1", get=fake_get, release_file=release_file, pyproject=pyproject) is None
    assert (release_file.read_text(), pyproject.read_text()) == before


def test_update_rejects_odd_versions(files):
    with pytest.raises(SystemExit, match="unexpected D2 version"):
        updater.update("nightly", get=fake_get, release_file=files[0], pyproject=files[1])
