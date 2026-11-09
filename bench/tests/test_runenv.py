from __future__ import annotations

import pytest

import pins as pinfile
import runenv

PINS = pinfile.load()


def test_the_runners_get_the_model_pins_whatever_the_shell_holds() -> None:
    environ = runenv.runner_environ(PINS, {"AWS_REGION": "ap-southeast-1", "HOME": "/h"})
    assert environ["AWS_REGION"] == PINS["AWS_REGION"]
    assert environ["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == PINS["ANTHROPIC_MODEL"]
    assert environ["HOME"] == "/h"
    with pytest.raises(SystemExit):
        runenv.runner_environ(PINS, {"BENCH_FORWARD_ENV": "AIDLC_UNATTENDED"})


def test_the_agent_env_is_the_forwarded_names_only() -> None:
    env = runenv.agent_env({"ANTHROPIC_MODEL": "m", "AWS_PROFILE": "p", "BENCH_FORWARD_ENV": "AWS_PROFILE", "PATH": "/bin", "AWS_REGION": ""})
    assert env == {"ANTHROPIC_MODEL": "m", "AWS_PROFILE": "p", "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "50000"}
    assert runenv.env_script({"A": "it's"}) == "export A='it'\"'\"'s'\n"
