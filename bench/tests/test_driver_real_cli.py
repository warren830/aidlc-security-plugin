"""The driver against the real Claude Code CLI the SDK bundles, with a fake model API.

Nothing leaves the machine: the CLI's model calls go to a local server
(fake_api.py) that plays the model's side from a script. This checks what the
fake CLI cannot: that Claude Code 2.1.318 asks the SDK about AskUserQuestion,
takes the driver's answers (a label, a list, free text), runs a /aidlc skill
with a multi-line request, and reports cumulative cost.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import claude_agent_sdk
import pytest
from fake_api import FakeApi, text, tool_use

from conftest import BENCH, STATE_PATH, read_jsonl

BUNDLED_CLI = Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
pytestmark = pytest.mark.skipif(not BUNDLED_CLI.exists(), reason="the SDK wheel bundles no CLI here")

SKILL = """---
name: aidlc
description: Test stand-in for the AI-DLC orchestrator skill.
user-invocable: true
---

ARGS-BEGIN $ARGUMENTS ARGS-END
"""
PROMPT = "Line one of the task.\n<pr_description>\nUse $HOME, `ticks`, 'single' and \"double\" quotes.\n</pr_description>"
QUESTIONS = [
    {
        "header": "Approval",
        "question": "Requirements complete. How would you like to proceed?",
        "multiSelect": False,
        "options": [{"label": "Approve", "description": "Continue"}, {"label": "Request Changes", "description": "Revise"}],
    },
    {
        "header": "Auth",
        "question": "Which logins should it support?",
        "multiSelect": True,
        "options": [
            {"label": "Email (Recommended)", "description": "a"},
            {"label": "SSO (Recommended)", "description": "b"},
            {"label": "None", "description": "c"},
        ],
    },
    {
        "header": "Name",
        "question": "What should the service be called?",
        "multiSelect": False,
        "options": [{"label": "svc-a", "description": "a"}, {"label": "svc-b", "description": "b"}],
    },
]


def write_state(lines: list[str]) -> str:
    directory = STATE_PATH.rsplit("/", 1)[0]
    quoted = " ".join(f"'{line}'" for line in lines)
    return f"mkdir -p {directory} && printf '%s\\n' {quoted} > {STATE_PATH}"


def request_text(request: dict) -> str:
    parts = []
    for message in request["messages"]:
        content = message["content"]
        for block in [{"type": "text", "text": content}] if isinstance(content, str) else content:
            if block.get("type") == "text":
                parts.append(block["text"])
            elif block.get("type") == "tool_result":
                inner = block.get("content")
                parts.append(inner if isinstance(inner, str) else json.dumps(inner))
    return "\n".join(parts)


def last_user_text(request: dict) -> str:
    user = [message for message in request["messages"] if message["role"] == "user"]
    return request_text({"messages": user[-1:]})


def test_the_real_cli_takes_the_scripted_answers_and_reports_running_totals(tmp_path: Path) -> None:
    project, home, out = tmp_path / "project", tmp_path / "home", tmp_path / "out"
    skill = project / ".claude/skills/aidlc/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(SKILL, encoding="utf-8")
    home.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    api = FakeApi(
        [
            tool_use("AskUserQuestion", {"questions": QUESTIONS}, "toolu_ask"),
            tool_use("Bash", {"command": write_state(["- **Status**: Running", "- [?] requirements-analysis"])}, "toolu_b1"),
            text("The requirements are ready. Do you approve them?"),
            tool_use("Bash", {"command": write_state(["- **Status**: Completed", "- [x] requirements-analysis"])}, "toolu_b2"),
            text("The workflow is complete."),
        ]
    )
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text(PROMPT, encoding="utf-8")
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "ANTHROPIC_BASE_URL": api.url,
        "ANTHROPIC_API_KEY": "sk-offline-test",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_TELEMETRY": "1",
        "DISABLE_AUTOUPDATER": "1",
    }
    try:
        done = subprocess.run(
            [
                sys.executable, str(BENCH / "bench.py"), "driver",
                "--local-cwd", str(project),
                "--claude-bin", str(BUNDLED_CLI),
                "--prompt-file", str(prompt_file),
                "--out-dir", str(out),
                "--timeout", "240",
                "--settle-seconds", "1",
                "--allowed-tools", "Bash,Read,Skill",
                "--first-message-template", "/aidlc --scope classic --project-type brownfield {prompt}",
            ],
            capture_output=True, text=True, timeout=300, env=env,
        )
    finally:
        api.close()
        (tmp_path / "api-requests.json").write_text(json.dumps(api.requests, indent=1), encoding="utf-8")

    assert done.returncode == 0, done.stderr
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert (summary["status"], summary["reason"]) == ("completed", "aidlc_complete"), summary
    requests = api.main_loop_requests()
    assert f"ARGS-BEGIN --scope classic --project-type brownfield {PROMPT} ARGS-END" in request_text(requests[0])
    after_ask = last_user_text(requests[1])
    for given in ('="Approve"', "Email (Recommended)", "SSO (Recommended)", '="Go with your recommendation."'):
        assert given in after_ask, after_ask
    assert last_user_text(requests[3]).endswith("Approve")
    rules = [(row["kind"], row["rule"]) for row in read_jsonl(out / "answers.jsonl")]
    assert rules == [
        ("ask_user_question", "approve"),
        ("ask_user_question", "recommended"),
        ("ask_user_question", "free_text"),
        ("prose_turn", "approve"),
    ]
    results = [frame for frame in read_jsonl(out / "raw.jsonl") if frame["type"] == "result"]
    assert len(results) == summary["results"] == 2
    assert results[1]["total_cost_usd"] > results[0]["total_cost_usd"] > 0
    assert summary["total_cost_usd"] == round(results[1]["total_cost_usd"], 6)
    assert summary["num_turns"] == results[0]["num_turns"] + results[1]["num_turns"]
