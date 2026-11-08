from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import bench
import pins as pinfile
from arms import ARMS
from baxbench import runner
from conftest import TESTS

PINS = pinfile.load()


def flags(argv: list[str]) -> dict[str, str]:
    return {argv[i]: argv[i + 1] for i in range(2, len(argv) - 1, 2)}


def test_the_arms_differ_only_in_their_setup_and_first_message(tmp_path: Path) -> None:
    work = bench.Work(tmp_path)
    argv = {
        label: bench.susvibes_argv(work, PINS, f"{label}-run1", tmp_path / label, tmp_path / f"setup-{label}.sh", tmp_path / label / "agent-driver", 8)
        for label in ARMS
    }
    differing = {name for name in flags(argv["arm1"]) if len({flags(a)[name] for a in argv.values()}) > 1}
    assert differing == {"--results_dir", "--model", "--setup_script", "--agent_driver"}


def test_the_susvibes_driver_wrapper_adds_the_arms_first_message(tmp_path: Path) -> None:
    wrapper = bench.driver_wrapper(tmp_path / "agent-driver", ARMS["arm2"].first_message_template("brownfield"))
    text = wrapper.read_text(encoding="utf-8")
    assert "driver --first-message-template '/aidlc --scope classic --project-type brownfield {prompt}' \"$@\"" in text
    assert subprocess.run(["bash", "-n", str(wrapper)], check=False).returncode == 0


def test_the_susvibes_command_passes_every_pin_to_the_fork(tmp_path: Path) -> None:
    work = bench.Work(tmp_path)
    argv = bench.susvibes_argv(work, PINS, "arm3-run2", tmp_path / "run", tmp_path / "s.sh", tmp_path / "d", 8)
    given = flags(argv)
    assert argv[1] == "parallel_batch_run.py"
    assert given["--jsonl_file"].endswith("datasets/default/susvibes_dataset.jsonl")
    assert given["--claude_code_version"] == "2.1.318"
    assert given["--timeout"] == PINS["TIMEOUT_SECONDS"]
    assert given["--strategy"] == "none"
    assert given["--setup_assets"] == str(work.assets)
    assert given["--num_processes"] == "8"


def test_predictions_merge_every_process_result(tmp_path: Path) -> None:
    for process, ids in ((0, ["a", "b"]), (1, ["c"])):
        final = tmp_path / "results" / "arm1-run1" / f"170000_process{process}" / "final_results.json"
        final.parent.mkdir(parents=True)
        final.write_text(json.dumps([{"instance_id": i, "model_name_or_path": "arm1-run1", "model_patch": "p", "claude_stdout": "x"} for i in ids]))
    merged = bench.predictions(tmp_path)
    assert [p["instance_id"] for p in merged] == ["a", "b", "c"]
    assert set(merged[0]) == {"instance_id", "model_name_or_path", "model_patch"}


def test_commands_need_the_setup_first(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="setup"):
        bench.main(["baxbench", "--arm", "arm1", "--work", str(tmp_path)])


def test_a_run_started_again_keeps_the_latest_record_per_instance(tmp_path: Path) -> None:
    for stamp, patch in (("1700000001_process0", "old"), ("1700000999_process0", "new")):
        final = tmp_path / "results" / "arm1-run1" / stamp / "final_results.json"
        final.parent.mkdir(parents=True)
        final.write_text(json.dumps([{"instance_id": "a", "model_name_or_path": "arm1-run1", "model_patch": patch}]))
    assert [p["model_patch"] for p in bench.predictions(tmp_path)] == ["new"]


def test_arm3_stops_before_any_container_without_the_security_agent_setup(tmp_path: Path) -> None:
    work = bench.Work(tmp_path)
    bench.preflight(ARMS["arm2"], work)
    with pytest.raises(SystemExit, match="Security Agent setup"):
        bench.preflight(ARMS["arm3"], work)
    (work.assets / "security-agent").mkdir(parents=True)
    (work.assets / "security-agent" / "config.json").write_text("{}")
    bench.preflight(ARMS["arm3"], work)


def test_the_baxbench_command_runs_each_task_then_both_baxbench_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work = bench.Work(tmp_path / "work")
    work.root.mkdir()
    pinfile.write_json(work.setup_manifest, {"commits": {"baxbench": "c"}, "assets": {"arch": "x64"}})
    export = json.loads((TESTS / "baxbench_export_sample.json").read_text())
    work.baxbench_tasks.write_text(json.dumps(export))
    wanted = tmp_path / "tasks.json"
    wanted.write_text(json.dumps({"tasks": [{"scenario": t["scenario"], "env": t["env"]} for t in export["tasks"]]}))
    work.baxbench.mkdir(parents=True)
    calls = tmp_path / "baxbench-calls.jsonl"
    fake_python = tmp_path / "python"
    fake_python.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {calls}\n")
    fake_python.chmod(0o755)
    monkeypatch.setattr(bench.Work, "baxbench_python", property(lambda self: fake_python))
    ran = []
    monkeypatch.setattr(runner, "run_task", lambda ctx, task: ran.append((ctx.arm.label, task.name)) or {"arm": ctx.arm.label})

    bench.baxbench(work, PINS, ARMS["arm1"], str(wanted), workers=2, force=False)

    assert sorted(ran) == sorted(("arm1", f"{t['scenario']}/{t['env']}") for t in export["tasks"])
    lines = calls.read_text().splitlines()
    assert [line.split("--mode ")[1].split()[0] for line in lines] == ["test"] * 4 + ["evaluate"] * 4
    manifest = json.loads((work.runs / "baxbench/results/arm1/manifest.json").read_text())
    assert manifest["arm"] == "arm1" and manifest["ended"] and manifest["pins"] == PINS
    assert (work.runs / "baxbench/results/arm1/setup-arm1.sh").read_text() == ARMS["arm1"].setup_script()


def test_baxbench_dockerfiles_get_the_apt_snapshot_after_every_from_and_a_pinned_goimports(tmp_path: Path) -> None:
    env = tmp_path / "src" / "env"
    env.mkdir(parents=True)
    (env / "go.py").write_text(
        'W = "/app"\nGO = f"""\nFROM golang:1.23-bullseye\nRUN mkdir -p {W}\nRUN go install golang.org/x/tools/cmd/goimports@latest\n"""\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "v1"], check=True)
    patch = bench.patch_baxbench_images(tmp_path, "20250811T000000Z", "v0.36.0")
    bench.patch_baxbench_images(tmp_path, "20250811T000000Z", "v0.36.0")
    namespace: dict = {}
    exec((env / "go.py").read_text(encoding="utf-8"), namespace)
    lines = namespace["GO"].splitlines()
    assert lines[1] == "FROM golang:1.23-bullseye"
    assert lines[3] == f"RUN {patch['apt_after_every_FROM']}"
    assert "debian-security/20250811T000000Z bullseye-security main\\n" in lines[3]
    assert lines.count(lines[3]) == 1
    assert "RUN go install golang.org/x/tools/cmd/goimports@v0.36.0" in lines
