# d2-bin

[![CI](https://github.com/lcmonteiro/d2-bin/actions/workflows/ci.yml/badge.svg)](https://github.com/lcmonteiro/d2-bin/actions/workflows/ci.yml)

The official [D2](https://d2lang.com) diagram binary, packaged as Python
wheels so `pip` and `uv` can install it like any other dependency: no Go, no
install script, no separate download.

```bash
uv add d2-bin            # or: pip install d2-bin
uv run d2 --version      # v0.7.1
uv run d2 flow.d2 flow.svg --theme=0 --layout=elk
```

```python
import d2_bin

d2_bin.executable()                              # path to the bundled d2
d2_bin.run("flow.d2", "flow.svg", "--theme=0")   # subprocess.run with check=True
d2_bin.D2_VERSION                                # "v0.7.1"
```

`python -m d2_bin ...` works as well.

## What is in a wheel

| Wheel | Contents |
|---|---|
| `linux` x86-64 / ARM64 (glibc and musl) | `d2_bin/bin/d2` |
| `macOS` Intel / Apple Silicon | `d2_bin/bin/d2` |
| `Windows` x86-64 / ARM64 | `d2_bin/bin/d2.exe` |

Every wheel holds the **unmodified official binary** of the pinned D2 release,
its license (`d2_bin/bin/D2-LICENSE.txt`, MPL-2.0) and a few lines of Python to
find and run it. The release archives are downloaded from
[terrastruct/d2 releases](https://github.com/terrastruct/d2/releases) and
checked against the SHA-256 hashes pinned in
[`src/d2_bin/d2_release.json`](src/d2_bin/d2_release.json) before they are
packaged; a mismatch fails the build.

## Versions

The package version is the D2 version it ships: `d2-bin 0.7.1` contains D2
`v0.7.1`. Packaging-only fixes are post-releases (`0.7.1.post1`). Pin it like
any dependency (`d2-bin==0.7.1`) to render identical diagrams everywhere.

A weekly workflow checks for a new D2 release and opens a pull request that
updates the version and the hashes.

## Building from source

Building a wheel (`uv build`, `pip install git+...`, an editable install)
downloads the D2 archive for the build platform, verifies it and bundles it.
Downloaded archives are cached (`D2_BIN_CACHE` overrides the folder).
`D2_BIN_PLATFORM=macos-arm64 uv build --wheel` builds for another platform;
the release workflow builds all six this way.

```bash
uv sync          # editable install; puts d2 in src/d2_bin/bin/ (git-ignored)
uv run pytest
```

## Releasing

1. Bump `version` in `pyproject.toml` (or merge the update PR), merge to `main`.
2. Push a tag `v<version>` (e.g. `v0.7.1`). The release workflow builds the six
   wheels and the sdist, smoke-tests them on Linux, macOS and Windows runners,
   and publishes to PyPI with
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) (no token).

One-time PyPI setup: add a trusted publisher for project `d2-bin`, owner
`lcmonteiro`, repository `d2-bin`, workflow `release.yml`, environment `pypi`.

## License

The packaging code is MIT ([LICENSE](LICENSE)). D2 itself is © Terrastruct,
Inc., under the Mozilla Public License 2.0, shipped unmodified; its source is at
<https://github.com/terrastruct/d2>. This project is not affiliated with
Terrastruct.
