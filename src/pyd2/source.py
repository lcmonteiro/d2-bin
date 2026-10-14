"""Check and tidy D2 source from Python.

    >>> import pyd2
    >>> pyd2.validate("a -> b")                 # raises D2Error if the diagram is invalid
    >>> pyd2.format("a->b")                     # 'a -> b\\n'
    >>> pyd2.format_file("flow.d2")             # rewrites the file; True if it changed
    >>> pyd2.format_file("flow.d2", check=True) # only reports whether it would change

``validate`` compiles the diagram the way rendering does, so it reports
everything a render would (unknown shapes, keywords or variables, bad
values, missing imports). ``d2 validate`` itself only checks the syntax in
D2 v0.7.1, so it is not used. ``format`` is ``d2 fmt``: it only parses, so
it accepts anything that is syntactically D2.
"""

from __future__ import annotations

from pathlib import Path

from .render import PathLike, _run

__all__ = ["format", "format_file", "validate", "validate_file"]

# Compiling means rendering; the SVG goes to stdout and is dropped. Plain settings keep it quick.
_COMPILE = ["--layout=dagre", "--pad=0", "--omit-version"]


def validate(source: str, *, cwd: PathLike | None = None, d2: str | None = None) -> None:
    """Raise :class:`~pyd2.D2Error` if D2 source text does not compile.

    ``cwd`` is where relative imports in the source are looked up.
    """
    _run([*_COMPILE, "-", "-"], "<text>", d2, input=source.encode("utf-8"), cwd=cwd)


def validate_file(source: PathLike, *, d2: str | None = None) -> None:
    """Raise :class:`~pyd2.D2Error` if a ``.d2`` file does not compile (imports resolve next to it)."""
    path = _existing(source)
    _run([*_COMPILE, path.name, "-"], path.name, d2, cwd=path.resolve().parent)  # see render_file


def format(source: str, *, d2: str | None = None) -> str:  # noqa: A001 - mirrors `d2 fmt`
    """D2 source text in D2's canonical layout; raises :class:`~pyd2.D2Error` if it does not parse."""
    return _format(source, "<text>", d2)


def format_file(source: PathLike, *, check: bool = False, d2: str | None = None) -> bool:
    """Format a ``.d2`` file in place; return True if it changed (or, with ``check``, would change).

    With ``check=True`` the file is left untouched, like ``d2 fmt --check``.
    Line endings are not a formatting change: a CRLF file stays CRLF.
    """
    path = _existing(source)
    with open(path, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    text = raw.replace("\r\n", "\n")
    formatted = _format(text, path.name, d2)
    if formatted == text:
        return False
    if not check:
        newline = "\r\n" if "\r\n" in raw else "\n"
        with open(path, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(formatted)
    return True


def _format(text: str, what: str, d2: str | None) -> str:
    out = _run(["fmt", "-"], what, d2, input=text.encode("utf-8")).stdout.decode("utf-8")
    return out or text  # d2 fmt prints nothing when the text is already formatted


def _existing(source: PathLike) -> Path:
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"no D2 file at {path}")
    return path
