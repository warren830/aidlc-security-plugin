#!/usr/bin/env python3
"""A recording stand-in for the docker commands the BaxBench runner uses.

Every call goes to FAKE_DOCKER_LOG with its stdin. Images exist once built.
`docker cp <container>:<dir>/code DEST` produces the app an agent would leave,
build output included, so the test can check what reaches BaxBench.
"""

import json
import os
import sys
from pathlib import Path

state = Path(os.environ["FAKE_DOCKER_STATE"])
args = sys.argv[1:]
stdin = sys.stdin.buffer.read() if not sys.stdin.isatty() and args[:1] in (["build"], ["exec"]) and ("-" in args or "-i" in args) else b""
with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": args, "stdin": stdin.decode(errors="replace") if args[:1] == ["exec"] else len(stdin)}) + "\n")

match args:
    case ["image", "inspect", tag]:
        sys.exit(0 if (state / tag.replace("/", "_")).exists() else 1)
    case ["build", "-t", tag, "-"]:
        state.mkdir(parents=True, exist_ok=True)
        (state / tag.replace("/", "_")).write_text("built")
    case ["run", *_]:
        print("0123456789ab")
    case ["cp", source, dest] if source.endswith(":/app/code"):
        app = Path(dest)
        (app / "node_modules" / "left-pad").mkdir(parents=True)
        (app / "node_modules" / "left-pad" / "index.js").write_text("module.exports = 1;\n")
        (app / "src").mkdir()
        (app / "src" / "main.rs").write_text("fn main() {}\n")
        (app / "aidlc-docs").mkdir()
        (app / "aidlc-docs" / "plan.md").write_text("# plan\n")
        (app / "CLAUDE.md").write_text("notes\n")
    case ["exec", *rest] if rest[-1].endswith("bash /opt/setup-env.sh") and os.environ.get("FAKE_SETUP_FAILS"):
        print("setup broke", file=sys.stderr)
        sys.exit(9)
