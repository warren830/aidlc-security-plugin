"""The environment the runners get, and the agent env that reaches a container.

Both benchmarks take the model from config.env, whatever the host shell holds.
The agent env follows the SusVibes fork's rule (briefs/contract.md and the
fork's run_docker.py get_agent_env): the forwarded names that are set and
not empty, and CLAUDE_CODE_MAX_OUTPUT_TOKENS at 50000 unless set. The BaxBench
runner applies the same rule itself; the fork applies it for SusVibes.
"""

from __future__ import annotations

import shlex
from collections.abc import Mapping

MODEL_PINS = (
    "CLAUDE_CODE_USE_BEDROCK",
    "AWS_REGION",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK",
)

AGENT_ENV_NAMES = (
    "CLAUDE_CODE_USE_BEDROCK",
    "AWS_REGION",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
    "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK",
)
MAX_OUTPUT_TOKENS = "50000"


def runner_environ(pins: Mapping[str, str], environ: Mapping[str, str]) -> dict[str, str]:
    forwarded = forwarded_extra(environ)
    if bypass := [name for name in forwarded if name.startswith("AIDLC_")]:
        raise SystemExit(f"BENCH_FORWARD_ENV names {', '.join(bypass)}: the protocol sets no AI-DLC switch")
    return {**environ, **{name: pins[name] for name in MODEL_PINS if pins.get(name)}}


def forwarded_extra(environ: Mapping[str, str]) -> list[str]:
    return [name.strip() for name in environ.get("BENCH_FORWARD_ENV", "").split(",") if name.strip()]


def agent_env(environ: Mapping[str, str]) -> dict[str, str]:
    names = [*AGENT_ENV_NAMES, *forwarded_extra(environ)]
    env = {name: environ[name] for name in names if environ.get(name)}
    env.setdefault("CLAUDE_CODE_MAX_OUTPUT_TOKENS", MAX_OUTPUT_TOKENS)
    return env


def env_script(env: Mapping[str, str]) -> str:
    return "".join(f"export {name}={shlex.quote(value)}\n" for name, value in env.items() if value)
