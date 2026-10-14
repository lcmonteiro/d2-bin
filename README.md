# pyd2

[![CI](https://github.com/lcmonteiro/pyd2/actions/workflows/ci.yml/badge.svg)](https://github.com/lcmonteiro/pyd2/actions/workflows/ci.yml)

[D2](https://d2lang.com) for Python: the official D2 diagram binary, packaged as
Python wheels so `pip` and `uv` can install it like any other dependency (no Go,
no install script, no separate download), plus a Python API to render diagrams.

```bash
uv add "pyd2 @ git+https://github.com/lcmonteiro/pyd2@v0.7.1"   # or: pip install "pyd2 @ git+..."
uv run d2 --version      # v0.7.1
uv run d2 flow.d2 flow.svg --theme=0 --layout=elk
```

## Python API

```python
from pyd2 import render, render_file

svg = render("user -> api: POST /reset", theme="c4", layout="elk")   # D2 text -> SVG text
render_file("flow.d2")                                               # flow.d2 -> flow.svg
render_file("flow.d2", "out/flow.svg", theme="Colorblind Clear", dark_theme="dark-mauve", sketch=True)
```

| Option | Default | Meaning |
|---|---|---|
| `theme` | `0` | theme by name (`"c4"`, `"Colorblind Clear"`) or [number](https://d2lang.com/tour/themes) |
| `dark_theme` | `None` | theme used when the viewer is in dark mode |
| `layout` | `"dagre"` | `"dagre"` or `"elk"` |
| `sketch` | `False` | hand-drawn look |
| `pad` | `100` | padding around the diagram, in pixels |
| `omit_version` | `True` | leave the D2 version out of the SVG, so output is the same everywhere |

The same options as an object: `Options(theme="c4", layout="elk")`, passed as
`render(text, opts)`; `Options(...).args()` gives the d2 flags.

- `render(text, cwd=...)`: where relative imports (`...@shared.d2`) are looked up.
- `d2=...`: run another d2 binary instead of the bundled one.
- Failures raise `D2Error`; its message is D2's error, `.stderr` the full output.
- `THEMES`, `LIGHT_THEMES`, `DARK_THEMES`, `theme_id("c4")` and `theme_name(303)`
  map theme names to numbers and back.

Lower level:

```python
import pyd2

pyd2.executable()                              # path to the bundled d2
pyd2.run("flow.d2", "flow.svg", "--theme=0")   # subprocess.run with check=True
pyd2.D2_VERSION                                # "v0.7.1"
```

`python -m pyd2 ...` works as well.

## What is in a wheel

| Wheel | Contents |
|---|---|
| `linux` x86-64 / ARM64 (glibc and musl) | `pyd2/bin/d2` |
| `macOS` Intel / Apple Silicon | `pyd2/bin/d2` |
| `Windows` x86-64 / ARM64 | `pyd2/bin/d2.exe` |

Every wheel holds the **unmodified official binary** of the pinned D2 release,
its license (`pyd2/bin/D2-LICENSE.txt`, MPL-2.0) and a small Python API to
find and run it. The release archives are downloaded from
[terrastruct/d2 releases](https://github.com/terrastruct/d2/releases) and
checked against the SHA-256 hashes pinned in
[`src/pyd2/d2_release.json`](src/pyd2/d2_release.json) before they are
packaged; a mismatch fails the build.

## Versions

The package version is the D2 version it ships: `pyd2 0.7.1` contains D2
`v0.7.1`. Packaging-only fixes are post-releases (`0.7.1.post1`). Pin it like
any dependency (`pyd2==0.7.1`) to render identical diagrams everywhere.

A weekly workflow checks for a new D2 release and opens a pull request that
updates the version and the hashes.

## Building from source

Building a wheel (`uv build`, `pip install git+...`, an editable install)
downloads the D2 archive for the build platform, verifies it and bundles it.
Downloaded archives are cached (`PYD2_CACHE` overrides the folder).
`PYD2_PLATFORM=macos-arm64 uv build --wheel` builds for another platform;
the release workflow builds all six this way.

```bash
uv sync          # editable install; puts d2 in src/pyd2/bin/ (git-ignored)
uv run pytest
```

## Releasing

1. Bump `version` in `pyproject.toml` (or merge the update PR), merge to `main`.
2. Push a tag `v<version>` (e.g. `v0.7.1`). The release workflow builds the six
   wheels and the sdist, smoke-tests them on Linux, macOS and Windows runners,
   and attaches them to a GitHub release for the tag.

pyd2 is not on PyPI: install it from git (above), which builds it for your
platform, or install a wheel from a GitHub release
(`uv pip install https://github.com/lcmonteiro/pyd2/releases/download/v0.7.1/<wheel>`).

## License

The packaging code is MIT ([LICENSE](LICENSE)). D2 itself is © Terrastruct,
Inc., under the Mozilla Public License 2.0, shipped unmodified; its source is at
<https://github.com/terrastruct/d2>. This project is not affiliated with
Terrastruct.
