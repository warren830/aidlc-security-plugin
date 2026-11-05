"""The driver's command line, as the SusVibes runner calls it (briefs/contract.md)."""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path

import anyio
from claude_agent_sdk import CanUseToolShadowedWarning

from driver.decide import STUCK_AFTER, Status
from driver.session import Session, Settings
from driver.transport import DockerTransport, LocalTransport, Transport
from driver.turns import SETTLE_SECONDS

PROMPT_SLOT = "{prompt}"
# Bypass and unattended switches the pre-registered protocol rules out.
FORBIDDEN_ENV_EXACT = ("AIDLC_UNATTENDED", "AIDLC_SKIP_HUMAN_PRESENCE_GUARD")
FORBIDDEN_ENV_PREFIX = "AIDLC_DISABLE_"
# The SDK waits this long for the CLI to answer `initialize`; a container's
# SessionStart hooks (AI-DLC, the plugin's compose step) run before it.
INITIALIZE_TIMEOUT_MS = "600000"
TERMINAL_OK = {Status.COMPLETED, Status.TIMEOUT, Status.STUCK}


def tools(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bench.py driver", description="Run Claude Code with a scripted user.")
    where = p.add_mutually_exclusive_group(required=True)
    where.add_argument("--container", help="docker container that runs claude")
    where.add_argument("--local-cwd", type=Path, help="run claude on this host, in this directory")
    p.add_argument("--workdir", help="work dir inside the container (docker transport)")
    p.add_argument("--claude-bin", default="claude", help="claude executable (local transport)")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=10800.0, help="seconds for the whole run")
    p.add_argument("--allowed-tools", type=tools, default=[])
    p.add_argument("--disallowed-tools", type=tools, default=[])
    p.add_argument("--source", action="append", default=[], help="file sourced before claude runs (repeatable)")
    p.add_argument(
        "--first-message-template",
        default=PROMPT_SLOT,
        help="first user message; {prompt} is replaced by the prompt file's text",
    )
    p.add_argument("--stuck-after", type=int, default=STUCK_AFTER)
    p.add_argument("--settle-seconds", type=float, default=SETTLE_SECONDS)
    return p


def forbidden_env(environ: dict[str, str]) -> list[str]:
    return sorted(
        name for name in environ if name in FORBIDDEN_ENV_EXACT or name.startswith(FORBIDDEN_ENV_PREFIX)
    )


def settings(args: argparse.Namespace, environ: dict[str, str]) -> Settings:
    p = parser()
    if args.first_message_template.count(PROMPT_SLOT) != 1:
        p.error(f"--first-message-template must contain {PROMPT_SLOT} exactly once")
    sources = tuple(args.source)
    transport: Transport
    if args.container:
        if not args.workdir:
            p.error("--container needs --workdir")
        transport = DockerTransport(container=args.container, workdir=args.workdir, sources=sources)
    else:
        if found := forbidden_env(environ):
            p.error(f"refusing to run with {', '.join(found)} set: the protocol uses no bypass")
        transport = LocalTransport(cwd=args.local_cwd.resolve(), claude_bin=args.claude_bin, sources=sources)
    prompt = args.prompt_file.read_text(encoding="utf-8")
    return Settings(
        transport=transport,
        first_message=args.first_message_template.replace(PROMPT_SLOT, prompt),
        out_dir=args.out_dir,
        timeout=args.timeout,
        allowed_tools=args.allowed_tools,
        disallowed_tools=args.disallowed_tools,
        stuck_after=args.stuck_after,
        settle_seconds=args.settle_seconds,
    )


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    run = settings(args, dict(os.environ))
    run.out_dir.mkdir(parents=True, exist_ok=True)
    # The SDK's version probe would run through the wrapper and land in raw.jsonl.
    os.environ["CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"] = "1"
    os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", INITIALIZE_TIMEOUT_MS)
    # Allowed tools skip the callback by design: only AskUserQuestion and the
    # calls `claude -p` would deny reach it.
    warnings.filterwarnings("ignore", category=CanUseToolShadowedWarning)
    summary = anyio.run(Session(run).run)
    return 0 if Status(summary["status"]) in TERMINAL_OK else 1
