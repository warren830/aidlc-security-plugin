from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

import pytest

import bench
import report

PILOT = Path(report.__file__).resolve().parent / "results" / "baxbench-pilot-2026-11-08"


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


def test_rows_csv_reads_back_as_the_rows_it_was_written_from(work: Path) -> None:
    files = report.write(work, work / "report", work / "eval", workers=8)
    written = report.baxbench_rows(work / "runs/baxbench") + report.susvibes_rows(work / "runs/susvibes", work / "eval")
    assert report.read_rows(files["rows"]) == written


def test_mcnemar_is_the_two_sided_binomial_test_on_the_discordant_pairs() -> None:
    assert report.mcnemar_exact(6, 0) == pytest.approx(2 / 64)
    assert report.mcnemar_exact(0, 6) == pytest.approx(2 / 64)
    assert report.mcnemar_exact(7, 1) == pytest.approx(2 * (1 + 8) / 256)
    assert report.mcnemar_exact(2, 2) == 1.0
    assert report.mcnemar_exact(0, 0) == 1.0


def bax(task: str, arm: str, status: str = "completed", func: bool | None = True, sec: bool | None = True,
        cost: float | None = 1.0, fix: int = 0, refused: int = 0) -> report.Row:
    wall = None if cost is None else cost * 60
    return report.Row("baxbench", task, arm, 1, status, func, sec, cost, None, None, None, None, wall,
                      fix_findings=fix, override_offered_and_refused=refused)


def test_compare_pairs_the_tasks_every_arm_scored_and_counts_where_arm2_and_arm3_differ(tmp_path: Path) -> None:
    rows = [bax(task, arm) for task in ("A/x", "B/x", "C/x", "D/x", "E/x", "F/x", "G/x") for arm in ("arm1", "arm2")]
    rows[rows.index(bax("C/x", "arm1"))] = bax("C/x", "arm1", sec=False)
    rows[rows.index(bax("C/x", "arm2"))] = bax("C/x", "arm2", sec=False)
    rows[rows.index(bax("E/x", "arm2"))] = bax("E/x", "arm2", status="error", func=False, sec=False, cost=None)
    rows += [
        bax("A/x", "arm3", cost=1.0),
        bax("B/x", "arm3", func=False, sec=False, cost=2.0, fix=2, refused=2),
        bax("C/x", "arm3", cost=3.0),
        bax("D/x", "arm3", status="stuck", cost=4.0),
        bax("E/x", "arm3"),
        bax("G/x", "arm3", status="error", func=None, sec=None, cost=None),
    ]
    (tmp_path / "rows.csv").write_text(report.to_csv([asdict(row) for row in rows]), encoding="utf-8")
    assert bench.main(["compare", str(tmp_path)]) == 0
    text = (tmp_path / "comparison.md").read_text(encoding="utf-8")
    assert "| arm2 | 7 | 6 | 7 | 1 | 0 |" in text
    assert "| arm3 | 6 | 5 | 5 | 0 | 1 |" in text
    assert "- `paired` has 4 tasks." in text
    assert "- `all completed` has 3 tasks." in text and "\n  - D/x, arm3 stuck\n" in text
    assert "| paired | arm2 | 4 | 4 | 3 | 3 / 4 | 4 | 0 | 0 | 0 |" in text
    assert "| paired | arm3 | 4 | 3 | 3 | 3 / 3 | 3 | 1 | 0 | 0 |" in text
    assert "| paired | func_pass | 4 | 1 | 0 | 3 | 0 | 1.000 |" in text
    assert "| paired | sec_pass | 4 | 1 | 1 | 2 | 0 | 1.000 |" in text
    assert "| paired | sec_pass where both pass func | 3 | 0 | 1 | 2 | 0 | 1.000 |" in text
    assert "| B/x | pass, pass | fail, fail | completed | 2 | 2 | yes |" in text
    assert "| C/x | pass, fail | pass, pass | completed | 0 | 0 | yes |" in text
    assert "| paired | arm3 | 2.50 | 2.50 | 3.70 | 10.00 | 2.50 | 2.50 | 3.70 |" in text
    assert "| paired | arm3 | 0 | 2 | 0 | 0 | 2 | 0 | 1 | 1 |" in text


def test_the_committed_pilot_comparison_is_what_compare_writes_from_its_rows() -> None:
    assert report.comparison(report.read_rows(PILOT / "rows.csv")) == (PILOT / "comparison.md").read_text(encoding="utf-8")
