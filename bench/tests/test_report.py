from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import report


def put(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def summary(status: str, cost: float, wall: float, approve: int = 0) -> dict:
    return {
        "status": status,
        "total_cost_usd": cost,
        "wall_seconds": wall,
        "usage": {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 4},
        "gate_stats": {"approve": approve, "prose_nudges": 1},
    }


def baxbench_task(work: Path, arm: str, scenario: str, env: str, driver: dict | None, tests: dict | None) -> None:
    out = work / "runs/baxbench/artifacts" / arm / scenario / env.replace("/", "-")
    put(out / "task.json", {"arm": arm, "scenario": scenario, "env": env})
    if driver is not None:
        put(out / "summary.json", driver)
    if tests is not None:
        sample = work / "runs/baxbench/results" / arm / scenario / env.replace("/", "-") / "temp0.2-openapi-none/sample0"
        put(sample / "test_results.json", tests)


def outcome(passed: int, total: int, cwes: list) -> dict:
    return {"num_passed_ft": passed, "num_total_ft": total, "num_ft_exceptions": 0, "num_total_st": 2, "num_st_exceptions": 0, "cwes": cwes}


@pytest.fixture
def work(tmp_path: Path) -> Path:
    baxbench_task(tmp_path, "arm1", "Calculator", "Go-net/http", summary("completed", 0.5, 100.0, approve=0), outcome(3, 3, []))
    baxbench_task(tmp_path, "arm1", "Login", "Python-Flask", None, None)
    baxbench_task(tmp_path, "arm2", "Calculator", "Go-net/http", summary("timeout", 2.0, 10800.0, approve=4), outcome(3, 3, [{"num": 89}]))
    final = tmp_path / "runs/susvibes/arm1-run2/results/arm1-run2/1700_process0/final_results.json"
    put(final, [
        {"instance_id": "a__b_1", "agent_summary": summary("completed", 1.0, 600.0)},
        {"instance_id": "a__b_2", "error": "Environment setup failed"},
    ])
    put(tmp_path / "eval/arm1-run2/none/arm1-run2/a__b_1/report.json", {"eval_status": "completed", "run": {"func": {"pass": True}, "sec": {"pass": False}}})
    return tmp_path


def test_every_task_run_becomes_a_row_with_its_verdict_and_cost(work: Path) -> None:
    rows = report.baxbench_rows(work / "runs/baxbench") + report.susvibes_rows(work / "runs/susvibes", work / "eval")
    by_task = {(row.benchmark, row.task, row.arm, row.run): row for row in rows}
    calc = by_task[("baxbench", "Calculator/Go-net/http", "arm1", 1)]
    assert (calc.status, calc.func_pass, calc.sec_pass, calc.cost_usd, calc.input_tokens) == ("completed", True, True, 0.5, 10)
    assert by_task[("baxbench", "Calculator/Go-net/http", "arm2", 1)].sec_pass is False
    assert by_task[("baxbench", "Login/Python-Flask", "arm1", 1)].status == "error"
    sus = by_task[("susvibes", "a__b_1", "arm1", 2)]
    assert (sus.func_pass, sus.sec_pass, sus.wall_seconds) == (True, False, 600.0)
    failed = by_task[("susvibes", "a__b_2", "arm1", 2)]
    assert (failed.status, failed.func_pass) == ("error", None)


def test_the_summary_gives_spread_rates_and_the_stop_condition(work: Path) -> None:
    rows = report.baxbench_rows(work / "runs/baxbench")
    arm1, arm2 = report.summarize(rows)
    assert (arm1["arm"], arm1["rows"], arm1["completed"], arm1["error"], arm1["timeout_rate"]) == ("arm1", 2, 1, 1, 0.0)
    assert (arm1["cost_mean"], arm1["cost_total"], arm1["func_pass_rate"], arm1["sec_pass_rate"]) == (0.5, 0.5, 1.0, 1.0)
    assert arm2["timeout_rate"] == 1.0 and arm2["over_stop_threshold"]
    assert arm2["approve"] == 4


def test_percentiles_interpolate_between_tasks() -> None:
    assert report.percentile([1.0], 0.9) == 1.0
    assert report.percentile([float(v) for v in range(1, 11)], 0.9) == pytest.approx(9.1)


def test_the_budget_scales_each_arms_pilot_mean_to_susvibes_in_full(work: Path) -> None:
    estimate = report.budget(report.summarize(report.baxbench_rows(work / "runs/baxbench")), "baxbench", workers=8)
    arm1, arm2, total = estimate
    assert arm1["tasks"] == 186 * 3
    assert arm1["cost_usd_at_mean"] == pytest.approx(0.5 * 558)
    assert arm2["cost_usd_at_mean"] == pytest.approx(2.0 * 558)
    assert arm1["wall_hours_with_workers"] == pytest.approx(100.0 * 558 / 3600 / 8)
    assert total["cost_usd_at_mean"] == pytest.approx(2.5 * 558)


def test_the_report_files_are_written_as_csv_and_markdown(work: Path) -> None:
    files = report.write(work, work / "report", work / "eval", workers=8)
    with files["rows"].open(encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 5
    text = files["report"].read_text(encoding="utf-8")
    assert "| baxbench | arm1 | 2 |" in text
    assert "a SusVibes task costs and takes what a pilot task cost and took in the same arm" in text
    assert "$1.16 per task" in text


def test_each_arm_counts_the_tasks_the_model_stopped_or_ended_by_refusing(tmp_path: Path) -> None:
    refused = summary("error", 0.3, 50.0) | {"model_refusals": {
        "safety_stops": 2, "refusal_stop_reasons": 1, "events": {"model_refusal_no_fallback": 1},
        "stopped_by_model": True, "ended_on_refusal": True,
    }}
    clean = summary("completed", 0.5, 100.0) | {"model_refusals": {
        "safety_stops": 0, "refusal_stop_reasons": 0, "events": {}, "stopped_by_model": False, "ended_on_refusal": False,
    }}
    baxbench_task(tmp_path, "arm3", "Calculator", "Go-net/http", refused, None)
    baxbench_task(tmp_path, "arm3", "Login", "Python-Flask", clean, None)
    baxbench_task(tmp_path, "arm3", "Forum", "Python-Flask", summary("completed", 0.5, 100.0), None)
    rows = report.baxbench_rows(tmp_path / "runs/baxbench")
    assert {row.task: row.safety_stops for row in rows}["Calculator/Go-net/http"] == 2
    (arm3,) = report.summarize(rows)
    assert (arm3["stopped_by_model"], arm3["ended_on_refusal"], arm3["other_model_answered"]) == (1, 1, 0)
