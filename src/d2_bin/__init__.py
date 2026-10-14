"""The official D2 diagram binary (https://d2lang.com), packaged for pip and uv.

    >>> import d2_bin
    >>> d2_bin.render("a -> b", theme="c4")       # D2 text -> SVG text
    >>> d2_bin.render_file("flow.d2")             # flow.d2 -> flow.svg
    >>> d2_bin.executable()                       # path to the bundled d2
    >>> d2_bin.run("in.d2", "out.svg", "--theme=0")

The package version follows the D2 release it ships (0.7.1 ships D2 v0.7.1;
packaging-only fixes are post-releases such as 0.7.1.post1).
"""

from __future__ import annotations

import json
import subprocess
import sys
from importlib import metadata, resources

__all__ = [
    "D2_VERSION",
    "DARK_THEMES",
    "LAYOUTS",
    "LIGHT_THEMES",
    "THEMES",
    "D2Error",
    "Options",
    "__version__",
    "executable",
    "render",
    "render_file",
    "run",
    "theme_id",
    "theme_name",
]

try:
    __version__ = metadata.version("d2-bin")
except metadata.PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0+unknown"

D2_VERSION: str = json.loads(resources.files(__name__).joinpath("d2_release.json").read_text(encoding="utf-8"))["version"]
"""The D2 release this package bundles, e.g. ``"v0.7.1"``."""


def executable() -> str:
    """Absolute path of the bundled ``d2`` binary.

    Raises FileNotFoundError when this installation has no binary (for example
    a source checkout that was never built).
    """
    name = "d2.exe" if sys.platform == "win32" else "d2"
    path = resources.files(__name__).joinpath("bin").joinpath(name)
    if not path.is_file():
        raise FileNotFoundError(
            f"the d2 binary is missing from {path}; reinstall d2-bin (e.g. `uv pip install --reinstall d2-bin`)"
        )
    return str(path)


def run(*args: str, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run the bundled d2 with ``args``; keyword arguments go to :func:`subprocess.run`."""
    return subprocess.run([executable(), *args], check=check, **kwargs)


# After executable() is defined: render.py uses it.
from .render import (  # noqa: E402
    DARK_THEMES,
    LAYOUTS,
    LIGHT_THEMES,
    THEMES,
    D2Error,
    Options,
    render,
    render_file,
    theme_id,
    theme_name,
)
