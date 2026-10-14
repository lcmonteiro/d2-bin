"""Render D2 to SVG from Python, with D2's options as plain arguments.

    >>> from pyd2 import render, render_file
    >>> svg = render("a -> b", theme="c4", layout="elk")      # D2 text -> SVG text
    >>> render_file("flow.d2", theme="dark-mauve")             # flow.d2 -> flow.svg

Themes are given by name (``"c4"``, ``"Colorblind Clear"``) or by D2 number.
Failures raise :class:`D2Error` with D2's own message.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from . import executable

__all__ = [
    "DARK_THEMES",
    "LAYOUTS",
    "LIGHT_THEMES",
    "THEMES",
    "D2Error",
    "Options",
    "render",
    "render_file",
    "theme_id",
    "theme_name",
]

# D2's built-in themes (`d2 themes`), by name. Any other number is passed to d2 as is.
LIGHT_THEMES = {
    "neutral-default": 0,
    "neutral-grey": 1,
    "flagship-terrastruct": 3,
    "cool-classics": 4,
    "mixed-berry-blue": 5,
    "grape-soda": 6,
    "aubergine": 7,
    "colorblind-clear": 8,
    "vanilla-nitro-cola": 100,
    "orange-creamsicle": 101,
    "shirley-temple": 102,
    "earth-tones": 103,
    "everglade-green": 104,
    "buttered-toast": 105,
    "terminal": 300,
    "terminal-grayscale": 301,
    "origami": 302,
    "c4": 303,
}
DARK_THEMES = {"dark-mauve": 200, "dark-flagship-terrastruct": 201}
THEMES = {**LIGHT_THEMES, **DARK_THEMES}
LAYOUTS = ("dagre", "elk")  # the layout engines built into d2

Theme = Union[int, str]
PathLike = Union[str, "os.PathLike[str]"]


class D2Error(RuntimeError):
    """d2 rejected the diagram or failed to run; ``stderr`` holds its full output."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


def theme_id(value: Theme) -> int:
    """A theme by name (``c4``, ``Colorblind Clear``, ``dark_mauve``) or number -> its D2 number."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str):
        name = value.strip().lower().replace(" ", "-").replace("_", "-")
        if name.isdigit():
            return int(name)
        if name in THEMES:
            return THEMES[name]
    raise ValueError(f"unknown D2 theme {value!r}; use a name ({', '.join(THEMES)}) or a number from `d2 themes`")


def theme_name(number: int) -> str:
    """The name of a built-in theme number, or the number itself as text."""
    return next((name for name, n in THEMES.items() if n == number), str(number))


@dataclass(frozen=True)
class Options:
    """How d2 renders: the same defaults as the d2 command, except the version is left out of the SVG.

    ``theme`` and ``dark_theme`` accept names or numbers and are stored as numbers.
    ``dark_theme`` is used when the viewer is in dark mode (None: no dark variant).
    """

    theme: Theme = 0
    dark_theme: Theme | None = None
    layout: str = "dagre"
    sketch: bool = False
    pad: int = 100
    omit_version: bool = True  # identical output across machines and d2 builds

    def __post_init__(self) -> None:
        object.__setattr__(self, "theme", theme_id(self.theme))
        if self.dark_theme is not None:
            object.__setattr__(self, "dark_theme", theme_id(self.dark_theme))
        if self.layout not in LAYOUTS:
            raise ValueError(f"unknown D2 layout {self.layout!r}; use {' or '.join(LAYOUTS)}")
        if isinstance(self.pad, bool) or not isinstance(self.pad, int) or self.pad < 0:
            raise ValueError(f"pad must be a whole number of pixels >= 0, not {self.pad!r}")

    def args(self) -> list[str]:
        """The d2 command-line flags for these options."""
        args = [f"--theme={self.theme}", f"--layout={self.layout}", f"--pad={self.pad}"]
        if self.omit_version:
            args.append("--omit-version")
        if self.dark_theme is not None:
            args.append(f"--dark-theme={self.dark_theme}")
        if self.sketch:
            args.append("--sketch")
        return args


def _options(options: Options | None, overrides: dict) -> Options:
    if options is not None and overrides:
        raise TypeError("pass either an Options object or option keywords, not both")
    return options if options is not None else Options(**overrides)


# d2 prefixes some errors with the Go function that raised them ("oss.terrastruct.com/d2/d2cli.validateCmd: ").
_GO_FUNC = re.compile(r"^\S+\.\w+Cmd: ")


def _run(args: list[str], what: str, d2: str | None, **kwargs) -> subprocess.CompletedProcess:
    proc = subprocess.run([d2 or executable(), *args], capture_output=True, check=False, **kwargs)
    if proc.returncode != 0:
        stderr = proc.stderr if isinstance(proc.stderr, str) else proc.stderr.decode("utf-8", "replace")
        lines = [line for line in stderr.strip().splitlines() if line.strip()]
        detail = _GO_FUNC.sub("", lines[-1].removeprefix("err: ")) if lines else f"exit code {proc.returncode}"
        raise D2Error(f"d2 failed on {what}: {detail}", stderr)
    return proc


def render(
    source: str,
    options: Options | None = None,
    *,
    cwd: PathLike | None = None,
    d2: str | None = None,
    **option_kwargs,
) -> str:
    """Render D2 source text to SVG text.

    ``cwd`` is where relative imports in the source (``...@shared.d2``) are
    looked up; ``d2`` runs another d2 binary instead of the bundled one.
    """
    opts = _options(options, option_kwargs)
    proc = _run([*opts.args(), "-", "-"], "<text>", d2, input=source.encode("utf-8"), cwd=cwd)
    return proc.stdout.decode("utf-8")


def render_file(
    source: PathLike,
    output: PathLike | None = None,
    options: Options | None = None,
    *,
    d2: str | None = None,
    **option_kwargs,
) -> Path:
    """Render a ``.d2`` file to SVG (default: next to it, ``.svg``); return the SVG path."""
    opts = _options(options, option_kwargs)
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"no D2 file at {source}")
    output = Path(output) if output is not None else source.with_suffix(".svg")
    output = output.resolve()
    # d2 runs next to the file: on Windows it mangles absolute input paths and then cannot resolve imports.
    _run([*opts.args(), source.name, str(output)], source.name, d2, text=True, cwd=source.resolve().parent)
    if not output.is_file():
        raise D2Error(f"d2 failed on {source.name}: no SVG was written to {output}")
    return output
