"""The experiment's pins (config.env) and the manifest every run writes beside its results."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
CONFIG = BENCH / "config.env"


def load(path: Path = CONFIG) -> dict[str, str]:
    pins: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.isidentifier():
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        pins[key] = value.strip().strip('"')
    return pins


def tools(value: str) -> list[str]:
    return [name for name in value.split(",") if name]


def git_head(path: Path) -> str | None:
    done = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def git_dirty(path: Path) -> bool:
    """Uncommitted changes in the checkout, so a manifest's commit may not be what ran."""
    done = subprocess.run(["git", "-C", str(path), "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(done.stdout.strip())


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def host() -> dict[str, str]:
    return {"name": socket.gethostname(), "machine": platform.machine(), "system": platform.platform()}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(partial, path)
