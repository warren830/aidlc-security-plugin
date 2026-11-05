#!/usr/bin/env python3
"""One command per arm: setup, baxbench, susvibes, report, and the driver itself."""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    if argv[:1] == ["driver"]:
        from driver.cli import main as driver_main

        return driver_main(argv[1:])
    print("usage: bench.py driver ...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
