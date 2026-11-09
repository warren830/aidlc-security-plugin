"""The report: one row per (benchmark, task, arm, run), a summary per arm, and the SusVibes budget.

Rows come from what the runs left on disk: the driver's summary.json, the
BaxBench runner's task.json and test_results.json, and the SusVibes runner's
final_results.json and the evaluator's report.json files.
"""

from __future__ import annotations

import csv
import io
import json
import statistics
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from baxbench import runner

GATES = ("approve", "fix_findings", "recommended", "free_text", "override_offered_and_refused", "prose_nudges")
SUSVIBES_TASKS = 186
SUSVIBES_RUNS = 3
ARMS = 3
# Leaderboard: Claude Code with Claude Sonnet 4 on SusVibes v0.0, mean total_cost_usd
# over its 200 public trajectories (attachment experiment-feasibility.md, section 5).
LEADERBOARD_COST_PER_TASK = 1.16
STOP_TIMEOUT_RATE = 0.30  # experiment-design.md section 6
# Tasks per arm that the model's safety systems stopped at least once, whose
# run ended on a refusal, or where a model other than the pinned one answered.
REFUSAL_FLAGS = ("stopped_by_model", "ended_on_refusal", "other_model_answered")


@dataclass
class Row:
    benchmark: str
    task: str
    arm: str
    run: int
    status: str
    func_pass: bool | None
    sec_pass: bool | None
    cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    cache_read_input_tokens: int | None
    cache_creation_input_tokens: int | None
    wall_seconds: float | None
    approve: int = 0
    fix_findings: int = 0
    recommended: int = 0
    free_text: int = 0
    override_offered_and_refused: int = 0
    prose_nudges: int = 0
    safety_stops: int | None = None
    stopped_by_model: bool | None = None
    ended_on_refusal: bool | None = None
    other_model_answered: bool | None = None


def read_json(path: Path) -> dict | list | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def from_summary(benchmark: str, task: str, arm: str, run: int, summary: dict | None, func: bool | None, sec: bool | None) -> Row:
    if summary is None:
        return Row(benchmark, task, arm, run, "error", func, sec, None, None, None, None, None, None)
    usage = summary.get("usage") or {}
    gates = summary.get("gate_stats") or {}
    refusals = summary.get("model_refusals")
    events = (refusals or {}).get("events") or {}
    return Row(
        benchmark, task, arm, run, summary["status"], func, sec,
        summary.get("total_cost_usd"),
        usage.get("input_tokens"), usage.get("output_tokens"),
        usage.get("cache_read_input_tokens"), usage.get("cache_creation_input_tokens"),
        summary.get("wall_seconds"),
        **{gate: gates.get(gate, 0) for gate in GATES},
        safety_stops=refusals["safety_stops"] if refusals else None,
        stopped_by_model=refusals["stopped_by_model"] if refusals else None,
        ended_on_refusal=refusals["ended_on_refusal"] if refusals else None,
        other_model_answered=bool(events.get("model_refusal_fallback") or events.get("model_fallback")) if refusals else None,
    )


def baxbench_verdict(test_results: dict | None) -> tuple[bool | None, bool | None]:
    """BaxBench's own rule (src/tasks.py SampleTestResult.record_result)."""
    if test_results is None:
        return None, None
    func = test_results["num_passed_ft"] == test_results["num_total_ft"]
    return func, func and not test_results["cwes"]


def baxbench_rows(run_root: Path) -> list[Row]:
    rows = []
    for record_path in sorted((run_root / "artifacts").glob("*/*/*/task.json")):
        record = read_json(record_path)
        out = record_path.parent
        task = runner.Task(record["scenario"], record["env"], "", "", "", {}, None)
        tests = read_json(runner.sample_dir(run_root / "results", record["arm"], task) / "test_results.json")
        rows.append(from_summary("baxbench", task.name, record["arm"], 1, read_json(out / "summary.json"), *baxbench_verdict(tests)))
    return rows


def susvibes_records(run_dir: Path) -> list[dict]:
    """Every record of the fork's runner in a run dir, in the order its processes wrote them."""
    records: list[dict] = []
    for final in sorted(run_dir.glob("results/*/*/final_results.json")):
        records += read_json(final) or []
    return records


def susvibes_rows(run_root: Path, eval_root: Path) -> list[Row]:
    rows = []
    for run_dir in sorted(path for path in run_root.glob("*-run*") if path.is_dir()):
        arm, _, run = run_dir.name.rpartition("-run")
        latest = {record["instance_id"]: record for record in susvibes_records(run_dir)}
        for instance_id, record in latest.items():
            verdict = read_json(eval_root / run_dir.name / "none" / run_dir.name / instance_id / "report.json")
            runs = (verdict or {}).get("run") or {}
            func = runs.get("func", {}).get("pass") if verdict else None
            sec = bool(func and runs.get("sec", {}).get("pass")) if verdict else None
            rows.append(from_summary("susvibes", instance_id, arm, int(run), record.get("agent_summary"), func, sec))
    return rows


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    cuts = statistics.quantiles(ordered, n=100, method="inclusive")
    return cuts[round(fraction * 100) - 1]


def spread(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p90": None, "total": None}
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p90": percentile(values, 0.9),
        "total": sum(values),
    }


def rate(flags: list[bool | None]) -> float | None:
    known = [flag for flag in flags if flag is not None]
    return sum(known) / len(known) if known else None


def summarize(rows: Iterable[Row]) -> list[dict]:
    groups: dict[tuple[str, str], list[Row]] = {}
    for row in rows:
        groups.setdefault((row.benchmark, row.arm), []).append(row)
    summary = []
    for (benchmark, arm), group in sorted(groups.items()):
        costs = [row.cost_usd for row in group if row.cost_usd is not None]
        walls = [row.wall_seconds for row in group if row.wall_seconds is not None]
        statuses = [row.status for row in group]
        timeout_rate = statuses.count("timeout") / len(group)
        entry: dict = {"benchmark": benchmark, "arm": arm, "rows": len(group)}
        entry |= {status: statuses.count(status) for status in ("completed", "timeout", "stuck", "error")}
        entry["timeout_rate"] = timeout_rate
        entry["over_stop_threshold"] = timeout_rate > STOP_TIMEOUT_RATE
        entry |= {f"cost_{key}": value for key, value in spread(costs).items()}
        entry |= {f"wall_{key}": value for key, value in spread(walls).items()}
        entry["func_pass_rate"] = rate([row.func_pass for row in group])
        entry["sec_pass_rate"] = rate([row.sec_pass for row in group])
        entry |= {gate: sum(getattr(row, gate) for row in group) for gate in GATES}
        entry |= {flag: sum(bool(getattr(row, flag)) for row in group) for flag in REFUSAL_FLAGS}
        summary.append(entry)
    return summary


def budget(summary: list[dict], benchmark: str, workers: int) -> list[dict]:
    """SusVibes v1.0 in full from one benchmark's per-arm means: 186 tasks x 3 runs per arm."""
    tasks = SUSVIBES_TASKS * SUSVIBES_RUNS
    lines = []
    for entry in (e for e in summary if e["benchmark"] == benchmark):
        if entry["cost_mean"] is None:
            continue
        lines.append(
            {
                "arm": entry["arm"],
                "tasks": tasks,
                "cost_usd_at_mean": entry["cost_mean"] * tasks,
                "cost_usd_at_p90": entry["cost_p90"] * tasks,
                "agent_hours_at_mean": entry["wall_mean"] * tasks / 3600 if entry["wall_mean"] is not None else None,
                "wall_hours_with_workers": entry["wall_mean"] * tasks / 3600 / workers if entry["wall_mean"] is not None else None,
            }
        )
    if lines:
        lines.append(
            {
                "arm": "all arms",
                "tasks": tasks * len(lines),
                "cost_usd_at_mean": sum(line["cost_usd_at_mean"] for line in lines),
                "cost_usd_at_p90": sum(line["cost_usd_at_p90"] for line in lines),
                "agent_hours_at_mean": sum(line["agent_hours_at_mean"] or 0 for line in lines),
                "wall_hours_with_workers": sum(line["wall_hours_with_workers"] or 0 for line in lines),
            }
        )
    return lines


def to_csv(records: list[dict]) -> str:
    if not records:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def table(records: list[dict], columns: list[str]) -> str:
    head = "| " + " | ".join(columns) + " |\n|" + "---|" * len(columns) + "\n"
    return head + "".join("| " + " | ".join(cell(record[c]) for c in columns) + " |\n" for record in records)


def markdown(rows: list[Row], summary: list[dict], estimate: list[dict], source: str) -> str:
    arm_columns = [
        "benchmark", "arm", "rows", "completed", "timeout", "stuck", "error", "timeout_rate", "over_stop_threshold",
        "cost_mean", "cost_median", "cost_p90", "cost_total", "wall_mean", "wall_median", "wall_p90",
        "func_pass_rate", "sec_pass_rate", *GATES, *REFUSAL_FLAGS,
    ]
    budget_columns = ["arm", "tasks", "cost_usd_at_mean", "cost_usd_at_p90", "agent_hours_at_mean", "wall_hours_with_workers"]
    leaderboard = LEADERBOARD_COST_PER_TASK * SUSVIBES_TASKS * SUSVIBES_RUNS * ARMS
    parts = [
        "# Benchmark report\n",
        f"{len(rows)} task runs. Costs are Claude Code's own estimates in USD (total_cost_usd). "
        "Times are the agent step's wall seconds, without the image build and the setup.\n",
        "## Per arm\n",
        table(summary, arm_columns),
        f"\n`over_stop_threshold` is a timeout rate above {STOP_TIMEOUT_RATE:.0%}, the design's stop condition. "
        "`stopped_by_model` counts the tasks the model's safety systems stopped at least once, `ended_on_refusal` "
        "the tasks whose run ended on a refusal, and `other_model_answered` the tasks where a model other than "
        "the pinned one answered a call; that last count should be 0.\n",
        f"## SusVibes v1.0 budget estimate, from the {source} pilot\n",
        "Assumption: a SusVibes task costs and takes what a pilot task cost and took in the same arm. "
        f"Each arm runs {SUSVIBES_TASKS} tasks {SUSVIBES_RUNS} times. Wall hours divide agent hours by the worker count.\n",
        table(estimate, budget_columns) if estimate else "No pilot costs yet.\n",
        f"\nCross-check: the SusVibes leaderboard's Claude Code run (Claude Sonnet 4, v0.0) averaged "
        f"${LEADERBOARD_COST_PER_TASK:.2f} per task; at that cost all {ARMS} arms x {SUSVIBES_RUNS} runs x "
        f"{SUSVIBES_TASKS} tasks come to ${leaderboard:,.0f}.\n",
    ]
    return "\n".join(parts)


def write(work: Path, out: Path, eval_root: Path, workers: int) -> dict[str, Path]:
    rows = baxbench_rows(work / "runs" / "baxbench") + susvibes_rows(work / "runs" / "susvibes", eval_root)
    summary = summarize(rows)
    estimate = budget(summary, "baxbench", workers)
    out.mkdir(parents=True, exist_ok=True)
    files = {"rows": out / "rows.csv", "summary": out / "summary.csv", "budget": out / "budget.csv", "report": out / "report.md"}
    files["rows"].write_text(to_csv([asdict(row) for row in rows]) or ",".join(f.name for f in fields(Row)) + "\n", encoding="utf-8")
    files["summary"].write_text(to_csv(summary), encoding="utf-8")
    files["budget"].write_text(to_csv(estimate), encoding="utf-8")
    files["report"].write_text(markdown(rows, summary, estimate, "BaxBench"), encoding="utf-8")
    return files
