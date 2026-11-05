from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import bench
import pins as pinfile
from arms import ARMS

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
