"""The driver end to end: the real Agent SDK against the fake `claude` (and fake `docker`)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from conftest import FAKE_CLAUDE, FAKE_DOCKER, STATE_PATH, install_aidlc, read_jsonl, run_driver, scenario, state

APPROVAL = {
    "header": "Approval",
    "question": "Requirements Analysis complete. How would you like to proceed?",
    "multiSelect": False,
    "options": [{"label": "Approve", "description": "Continue"}, {"label": "Request Changes", "description": "Revise"}],
}


def options(*labels: str) -> list[dict]:
    return [{"label": label, "description": ""} for label in labels]


def usage_entry(cost: float, inp: int, out: int) -> dict:
    return {
        "fake-model": {
            "inputTokens": inp,
            "outputTokens": out,
            "cacheReadInputTokens": 5,
            "cacheCreationInputTokens": 7,
            "costUSD": cost,
        }
    }


def test_without_aidlc_the_first_settled_result_completes_the_run(project: Path) -> None:
    scenario(
        project,
        [
            {"say": "Implemented."},
            {"result": {"cost": 0.25, "num_turns": 3, "model_usage": usage_entry(0.25, 100, 20)}},
        ],
    )
    run = run_driver(project, "--allowed-tools", "Bash,Edit", "--disallowed-tools", "mcp__security-agent__setup")

    assert run.code == 0, run.stderr
    summary = run.summary
    assert (summary["status"], summary["reason"]) == ("completed", "no_aidlc")
    assert summary["total_cost_usd"] == 0.25
    assert summary["num_turns"] == 3
    assert summary["results"] == 1
    assert summary["usage"] == {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_input_tokens": 5,
        "cache_creation_input_tokens": 7,
    }
    assert summary["aidlc"] == {"detected": False, "completed": False, "final_state_excerpt": ""}
    assert run.user_messages == ["Build the feature."]
    argv = run.fake_start["argv"]
    assert "--system-prompt" not in argv
    assert argv[argv.index("--allowedTools") + 1] == "Bash,Edit"
    assert argv[argv.index("--disallowedTools") + 1] == "mcp__security-agent__setup"
    assert argv[argv.index("--permission-prompt-tool") + 1] == "stdio"
    assert "--setting-sources=user,project,local" in argv
    raw = read_jsonl(run.out / "raw.jsonl")
    assert [frame["type"] for frame in raw if frame["type"] in ("assistant", "result")] == ["assistant", "result"]
    assert run.answers == []


def test_aidlc_gates_are_answered_by_the_rule_table_until_the_workflow_completes(project: Path) -> None:
    install_aidlc(project)
    scenario(
        project,
        [
            {"ask": [APPROVAL]},
            {"ask": [{"header": "Sensors", "question": "A blocking check failed.", "options": options("Fix findings", "Override blocking sensors (Recommended)")}]},
            {"ask": [{"header": "Finding", "question": "SQL injection in app.py", "options": options("Fix it", "Accept the risk")}]},
            {
                "ask": [
                    {"header": "Database", "question": "Which database?", "options": options("Postgres (Recommended)", "SQLite")},
                    {"header": "Auth", "question": "Which logins?", "multiSelect": True, "options": options("Email (Recommended)", "SSO (Recommended)", "None")},
                    {"header": "Name", "question": "What should the service be called?", "options": options("svc-a", "svc-b")},
                ]
            },
            {"write": {"path": STATE_PATH, "text": state("- [?] requirements-analysis")}},
            {"say": "The requirements are ready for your approval. Approve?"},
            {"result": {"cost": 0.5, "num_turns": 4}},
        ],
        [
            {"write": {"path": STATE_PATH, "text": state("- [x] requirements-analysis", status="Completed")}},
            {"say": "Workflow complete."},
            {"result": {"cost": 0.9, "num_turns": 2}},
        ],
    )
    run = run_driver(project, "--first-message-template", "/aidlc --scope classic --project-type greenfield {prompt}")

    assert run.code == 0, run.stderr
    assert run.user_messages == ["/aidlc --scope classic --project-type greenfield Build the feature.", "Approve"]
    given = [entry["response"]["response"]["updatedInput"]["answers"] for entry in run.permissions]
    assert given == [
        {APPROVAL["question"]: "Approve"},
        {"A blocking check failed.": "Fix findings"},
        {"SQL injection in app.py": "Fix it"},
        {
            "Which database?": "Postgres (Recommended)",
            "Which logins?": ["Email (Recommended)", "SSO (Recommended)"],
            "What should the service be called?": "Go with your recommendation.",
        },
    ]
    assert [(row["kind"], row["rule"]) for row in run.answers] == [
        ("ask_user_question", "approve"),
        ("ask_user_question", "fix_findings"),
        ("ask_user_question", "fix_findings"),
        ("ask_user_question", "recommended"),
        ("ask_user_question", "recommended"),
        ("ask_user_question", "free_text"),
        ("prose_turn", "approve"),
    ]
    assert run.answers[1]["refused"] == ["Override blocking sensors (Recommended)"]
    assert run.answers[-1]["awaiting_stage"] == "requirements-analysis"
    summary = run.summary
    assert (summary["status"], summary["reason"]) == ("completed", "aidlc_complete")
    assert summary["gate_stats"] == {
        "approve": 2,
        "fix_findings": 2,
        "recommended": 2,
        "free_text": 1,
        "override_offered_and_refused": 2,
        "prose_nudges": 1,
    }
    assert summary["total_cost_usd"] == 0.9
    assert summary["num_turns"] == 6
    assert summary["results"] == 2
    assert summary["aidlc"]["detected"] and summary["aidlc"]["completed"]
    assert "- **Status**: Completed" in summary["aidlc"]["final_state_excerpt"]


def test_a_result_with_a_subagent_still_running_waits_for_its_report(project: Path) -> None:
    scenario(
        project,
        [
            {"task_started": {"task_id": "t1", "task_type": "local_agent"}},
            {"say": "The agent is working."},
            {"result": {"cost": 0.1}},
            {"sleep": 1.5},
            {"task_notification": {"task_id": "t1"}},
            {"say": "The agent reported."},
            {"result": {"cost": 0.2}},
        ],
    )
    run = run_driver(project)

    assert run.code == 0, run.stderr
    assert run.user_messages == ["Build the feature."]
    assert (run.summary["status"], run.summary["results"], run.summary["total_cost_usd"]) == ("completed", 2, 0.2)


def test_a_finished_but_unreported_subagent_holds_the_turn_only_for_the_settle_wait(project: Path) -> None:
    scenario(
        project,
        [
            {"task_started": {"task_id": "t1", "task_type": "local_agent"}},
            {"task_updated": {"task_id": "t1", "status": "completed"}},
            {"result": {"cost": 0.1}},
        ],
    )
    started = time.monotonic()
    run = run_driver(project, "--settle-seconds", "1.5")

    assert run.code == 0, run.stderr
    assert run.summary["status"] == "completed"
    assert time.monotonic() - started >= 1.5


def test_a_background_shell_does_not_hold_the_turn_open(project: Path) -> None:
    scenario(
        project,
        [
            {"task_started": {"task_id": "server", "task_type": "local_bash"}},
            {"result": {"cost": 0.1}},
        ],
    )
    run = run_driver(project, "--timeout", "20")

    assert run.code == 0, run.stderr
    assert (run.summary["status"], run.summary["reason"]) == ("completed", "no_aidlc")


def test_prose_nudges_that_change_nothing_end_the_run_as_stuck(project: Path) -> None:
    install_aidlc(project)
    unchanged = [{"write": {"path": STATE_PATH, "text": state("- [-] requirements-analysis")}}, {"say": "Which option, 1-6?"}, {"result": {"cost": 0.1}}]
    scenario(project, *[unchanged] * 6)
    run = run_driver(project, "--stuck-after", "3")

    assert run.code == 0, run.stderr
    assert (run.summary["status"], run.summary["reason"]) == ("stuck", "prose_nudges_without_progress")
    assert run.user_messages[1:] == ["Go with your recommendation."] * 3
    assert run.summary["gate_stats"]["prose_nudges"] == 3
    assert [row["question"].strip() for row in run.answers] == ["Which option, 1-6?"] * 3


def test_a_question_asked_again_and_again_ends_the_run_as_stuck(project: Path) -> None:
    install_aidlc(project)
    autonomy = {"header": "Autonomy", "question": "How should I continue?", "options": options("Continue automatically", "Review each checkpoint")}
    scenario(project, [*[{"ask": [autonomy]}] * 6, {"result": {"cost": 0.1}}])
    run = run_driver(project, "--stuck-after", "3")

    assert run.code == 0, run.stderr
    assert (run.summary["status"], run.summary["reason"]) == ("stuck", "question_reasked")
    assert [entry["response"]["response"]["behavior"] for entry in run.permissions] == ["allow"] * 3 + ["deny"]
    assert len(run.user_messages) == 1


def test_the_timeout_interrupts_the_turn_and_counts_as_a_terminal_status(project: Path) -> None:
    scenario(project, [{"say": "Working on it."}, {"result": {"cost": 0.3}}, {"sleep": 60}])
    install_aidlc(project)
    started = time.monotonic()
    run = run_driver(project, "--timeout", "3")

    assert run.code == 0, run.stderr
    assert (run.summary["status"], run.summary["reason"]) == ("timeout", "deadline")
    assert "interrupt" in [entry["event"] for entry in run.fake_log]
    assert run.summary["total_cost_usd"] == 0.3
    assert time.monotonic() - started < 30


def test_a_cli_that_ignores_the_interrupt_is_killed(project: Path) -> None:
    scenario(project, [{"say": "Working on it."}, {"hang": True}])
    started = time.monotonic()
    run = run_driver(project, "--timeout", "2")

    assert run.code == 0, run.stderr
    assert run.summary["status"] == "timeout"
    assert time.monotonic() - started < 60


def test_other_tools_that_need_permission_are_denied_as_claude_p_would(project: Path) -> None:
    scenario(project, [{"tool": {"name": "WebSearch", "input": {"query": "fix"}}}, {"result": {"cost": 0.1}}])
    run = run_driver(project)

    assert run.code == 0, run.stderr
    assert run.permissions[0]["response"]["response"]["behavior"] == "deny"
    assert run.summary["permission_denials"] == {"WebSearch": 1}
    assert [row["tool"] for row in read_jsonl(run.out / "permissions.jsonl")] == ["WebSearch"]


def test_an_error_result_ends_the_run_as_an_error(project: Path) -> None:
    scenario(project, [{"result": {"is_error": True, "subtype": "success", "errors": ["API Error: 529 overloaded"]}}])
    run = run_driver(project)

    assert run.code == 1
    assert (run.summary["status"], run.summary["reason"]) == ("error", "error_result")
    assert "529" in run.summary["error"]


def test_a_cli_that_exits_mid_turn_is_a_driver_error_with_a_summary(project: Path) -> None:
    scenario(project, [{"say": "about to crash"}, {"exit": 3}])
    run = run_driver(project)

    assert run.code == 1
    assert run.summary["status"] == "error"
    assert run.summary["reason"] in ("cli_exited", "cli_failed")


def test_an_unattended_or_bypass_switch_in_the_environment_is_refused(project: Path) -> None:
    scenario(project, [{"result": {"cost": 0.1}}])
    run = run_driver(project, env={"AIDLC_DISABLE_PLAN_APPROVAL_GUARD": "1"})

    assert run.code == 2
    assert "AIDLC_DISABLE_PLAN_APPROVAL_GUARD" in run.stderr
    assert run.fake_log == []


def test_the_first_message_template_must_hold_the_prompt_slot(project: Path) -> None:
    scenario(project, [{"result": {"cost": 0.1}}])
    run = run_driver(project, "--first-message-template", "/aidlc --scope classic")

    assert run.code == 2
    assert "{prompt}" in run.stderr


def docker_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").symlink_to(FAKE_DOCKER)
    (bin_dir / "claude").symlink_to(FAKE_CLAUDE)
    return bin_dir


def test_the_docker_transport_forwards_only_the_sdk_variables_and_sources_each_file(project: Path, tmp_path: Path) -> None:
    install_aidlc(project)
    scenario(
        project,
        [
            {"write": {"path": STATE_PATH, "text": state("- [x] requirements-analysis", status="Completed")}},
            {"result": {"cost": 0.4}},
        ],
    )
    sourced = tmp_path / "agent-env.sh"
    sourced.write_text("echo NOISE\nexport FAKE_SOURCED=from-source-file\n", encoding="utf-8")
    bin_dir = docker_bin(tmp_path)
    home = tmp_path / "container-home"
    home.mkdir()
    docker_log = tmp_path / "docker.jsonl"
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_DOCKER_PATH": f"{bin_dir}:/usr/bin:/bin",
        "FAKE_DOCKER_HOME": str(home),
        "FAKE_DOCKER_LOG": str(docker_log),
        "BENCH_TEST_HOST_SECRET": "must-not-cross",
    }
    run = run_driver(
        project,
        "--container", "bench-test-1",
        "--workdir", str(project),
        "--source", str(sourced),
        "--source", "/no/such/file",
        env=env,
        local=False,
    )

    assert run.code == 0, run.stderr
    assert (run.summary["status"], run.summary["reason"]) == ("completed", "aidlc_complete")
    container_env = run.fake_start["env"]
    assert container_env["FAKE_CONTAINER"] == "bench-test-1"
    assert container_env["FAKE_SOURCED"] == "from-source-file"
    assert container_env["CLAUDE_CODE_ENTRYPOINT"] == "sdk-py"
    assert container_env["CLAUDE_CODE_SDK_READS_SESSION_STATE"] == "1"
    assert "BENCH_TEST_HOST_SECRET" not in container_env
    calls = read_jsonl(docker_log)
    claude_call, *probe_calls = calls
    assert "must-not-cross" not in json.dumps(calls)
    forwarded = {claude_call["argv"][i + 1] for i, arg in enumerate(claude_call["argv"]) if arg == "-e"}
    added = set(claude_call["env_names"]) - set(env) - set(os.environ) - {"SHLVL", "_", "PWD", "OLDPWD"}
    changed = {name for name, value in claude_call["claude_env"].items() if os.environ.get(name, value) != value}
    set_by_driver = {"CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT"}
    assert (added | changed) - set_by_driver == forwarded
    assert all(call["argv"][:2] == ["exec", "-w"] and call["argv"][3] == "bench-test-1" for call in probe_calls)
    raw = (run.out / "raw.jsonl").read_text(encoding="utf-8")
    assert "NOISE" not in raw
    assert all(line.startswith("{") for line in raw.splitlines())
