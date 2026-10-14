"""``d2`` / ``python -m pyd2``: run the bundled D2 binary with the given arguments."""

from __future__ import annotations

import os
import subprocess
import sys

from . import executable


def main() -> None:
    try:
        exe = executable()
    except FileNotFoundError as exc:
        sys.exit(f"pyd2: {exc}")
    args = [exe, *sys.argv[1:]]
    if sys.platform == "win32":
        # Windows has no exec(); run d2 as a child and pass its exit code through.
        sys.exit(subprocess.call(args))
    os.execv(exe, args)


if __name__ == "__main__":
    main()
