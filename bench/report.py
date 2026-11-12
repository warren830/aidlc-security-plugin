"""The report: one row per (benchmark, task, arm, run), a summary per arm, and the SusVibes budget.

Rows come from what the runs left on disk: the driver's summary.json, the
BaxBench runner's task.json and test_results.json, and the SusVibes runner's
final_results.json and the evaluator's report.json files. The comparison of
the plugin off and on reads them back from rows.csv.
"""

from __future__ import annotations

import csv
import io
import json
import math
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
# arm2 runs AI-DLC with the plugin off, arm3 adds the plugin, and arm1, Claude
# Code alone, is the reference.
REFERENCE, OFF, ON = "arm1", "arm2", "arm3"
COMPARED = (REFERENCE, OFF, ON)


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


def read_rows(path: Path) -> list[Row]:
    """rows.csv as write() leaves it: an empty cell is None, and True and False are booleans."""
    kinds = {field.name: str(field.type).split(" | ")[0] for field in fields(Row)}
    parse = {"bool": lambda text: text == "True", "int": int, "float": float, "str": str}
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            Row(**{name: None if text == "" else parse[kinds[name]](text) for name, text in record.items()})
            for record in csv.DictReader(handle)
        ]


def scored(row: Row | None) -> bool:
    """The agent ran, so the driver left a summary with its cost, and BaxBench tested the app."""
    return row is not None and row.cost_usd is not None and row.func_pass is not None


@dataclass(frozen=True)
class TaskSet:
    name: str
    rule: str
    tasks: tuple[str, ...]


def task_sets(arms_by_task: dict[str, dict[str, Row]]) -> tuple[TaskSet, TaskSet]:
    paired = tuple(sorted(task for task, arms in arms_by_task.items() if all(scored(arms.get(arm)) for arm in COMPARED)))
    completed = tuple(task for task in paired if all(arms_by_task[task][arm].status == "completed" for arm in COMPARED))
    return (
        TaskSet("paired", "Every arm ran the agent, and BaxBench scored the app", paired),
        TaskSet("all completed", "These are the paired tasks where every arm's run ended `completed`", completed),
    )


def mcnemar_exact(off_only: int, on_only: int) -> float:
    """Two-sided exact McNemar test: the binomial test of the discordant pairs at one half."""
    pairs = off_only + on_only
    tail = sum(math.comb(pairs, k) for k in range(min(off_only, on_only) + 1))
    return min(1.0, 2 * tail / 2**pairs)


def verdicts(row: Row) -> str:
    return ", ".join("pass" if passed else "fail" for passed in (row.func_pass, row.sec_pass))


def comparison(rows: list[Row]) -> str:
    """arm2, the plugin off, against arm3, the plugin on, task by task on BaxBench, with arm1 for reference."""
    arms_by_task: dict[str, dict[str, Row]] = {}
    for row in rows:
        if row.benchmark == "baxbench":
            arms_by_task.setdefault(row.task, {})[row.arm] = row
    sets = task_sets(arms_by_task)
    paired, completed = sets

    accounting = []
    for arm in COMPARED:
        present = [arms[arm] for arms in arms_by_task.values() if arm in arms]
        accounting.append({
            "arm": arm,
            "rows": len(present),
            "agent ran": sum(row.cost_usd is not None for row in present),
            "BaxBench verdict": sum(row.func_pass is not None for row in present),
            "verdict, no agent run": sum(row.func_pass is not None and row.cost_usd is None for row in present),
            "no row": len(arms_by_task) - len(present),
        })

    passes, costs, gates, contrasts = [], [], [], []
    for task_set in sets:
        for arm in COMPARED:
            group = [arms_by_task[task][arm] for task in task_set.tasks]
            func = sum(bool(row.func_pass) for row in group)
            sec = sum(bool(row.sec_pass) for row in group)
            statuses = [row.status for row in group]
            passes.append({
                "set": task_set.name, "arm": arm, "tasks": len(group), "func_pass": func, "sec_pass": sec,
                "sec_pass among func_pass": f"{sec} / {func}",
                **{status: statuses.count(status) for status in ("completed", "stuck", "timeout")},
                "stopped_by_model": sum(bool(row.stopped_by_model) for row in group),
            })
            dollars = spread([row.cost_usd for row in group if row.cost_usd is not None])
            minutes = spread([row.wall_seconds / 60 for row in group if row.wall_seconds is not None])
            costs.append({
                "set": task_set.name, "arm": arm,
                **{f"cost {key}": dollars[key] for key in ("mean", "median", "p90", "total")},
                **{f"minutes {key}": minutes[key] for key in ("mean", "median", "p90")},
            })
            gates.append({
                "set": task_set.name, "arm": arm,
                **{gate: sum(getattr(row, gate) for row in group) for gate in GATES},
                "tasks with fix_findings": sum(row.fix_findings > 0 for row in group),
                "tasks with a refused override": sum(row.override_offered_and_refused > 0 for row in group),
            })
        both_func = tuple(task for task in task_set.tasks if all(arms_by_task[task][arm].func_pass for arm in (OFF, ON)))
        for measure, tasks, field in (
            ("func_pass", task_set.tasks, "func_pass"),
            ("sec_pass", task_set.tasks, "sec_pass"),
            ("sec_pass where both pass func", both_func, "sec_pass"),
        ):
            outcomes = [(bool(getattr(arms_by_task[task][OFF], field)), bool(getattr(arms_by_task[task][ON], field))) for task in tasks]
            off_only = sum(off and not on for off, on in outcomes)
            on_only = sum(on and not off for off, on in outcomes)
            contrasts.append({
                "set": task_set.name, "measure": measure, "tasks": len(tasks),
                f"{OFF} only": off_only, f"{ON} only": on_only,
                "both": sum(off and on for off, on in outcomes), "neither": sum(not (off or on) for off, on in outcomes),
                "exact McNemar p": f"{mcnemar_exact(off_only, on_only):.3f}",
            })

    differ = [
        {
            "task": task,
            f"{OFF} func, sec": verdicts(arms_by_task[task][OFF]),
            f"{ON} func, sec": verdicts(arms_by_task[task][ON]),
            f"{ON} status": arms_by_task[task][ON].status,
            f"{ON} fix_findings": arms_by_task[task][ON].fix_findings,
            f"{ON} overrides refused": arms_by_task[task][ON].override_offered_and_refused,
            "in all completed": task in completed.tasks,
        }
        for task in paired.tasks
        if verdicts(arms_by_task[task][OFF]) != verdicts(arms_by_task[task][ON])
    ]
    left_out = [
        f"  - {task}, " + ", ".join(f"{arm} {arms_by_task[task][arm].status}" for arm in COMPARED if arms_by_task[task][arm].status != "completed")
        for task in paired.tasks
        if task not in completed.tasks
    ]

    def columns(records: list[dict]) -> str:
        return table(records, list(records[0]))

    return "\n".join([
        "# BaxBench: the plugin off and on\n",
        "Written by `python bench/bench.py compare <folder>` from the folder's `rows.csv`. Do not edit it by hand. "
        f"{REFERENCE} is Claude Code alone, for reference. {OFF} adds AI-DLC and is the plugin off. "
        f"{ON} adds AI-DLC and the security plugin and is the plugin on.\n",
        "## Rows per arm\n",
        f"Tasks are the {len(arms_by_task)} that have a row in any arm. An agent ran when the driver left a summary, "
        "which carries the cost. A verdict with no agent run means that BaxBench tested the app folder of an agent "
        "that never started, as when the setup fails.\n",
        columns(accounting),
        "## Task sets\n",
        f"- `{paired.name}` has {len(paired.tasks)} tasks. {paired.rule}.",
        f"- `{completed.name}` has {len(completed.tasks)} tasks. {completed.rule}. "
        + ("It leaves out these paired tasks, with the arms whose run ended otherwise:" if left_out else "It leaves out no paired task."),
        *left_out,
        "",
        "## Pass counts\n",
        "BaxBench's `sec_pass` needs `func_pass` and no CWE, so a task that fails the functional tests fails both.\n",
        columns(passes),
        f"## {OFF} against {ON}, task by task\n",
        f"`{OFF} only` counts the tasks that pass in {OFF} and fail in {ON}, and `{ON} only` the reverse. "
        "The p-value is the two-sided exact McNemar test on those two counts. Each arm ran each task once, "
        "so the test cannot tell the arm's effect from the variation between two runs of one arm. "
        "Read it as a description of how one-sided the differing tasks are, not as a significance test.\n",
        columns(contrasts),
        f"## Paired tasks where {OFF} and {ON} differ\n",
        columns(differ) if differ else "None.\n",
        "## Cost and time per task\n",
        "Cost is Claude Code's own estimate in USD (`total_cost_usd`). Minutes are the agent step's wall time, "
        "without the image build and the setup.\n",
        columns(costs),
        "## Gate answers\n",
        "The driver's answers by rule, summed over the set. `override_offered_and_refused` counts the questions "
        "that offered an override, which the driver never chooses.\n",
        columns(gates),
    ])


def write_comparison(results: Path) -> Path:
    out = results / "comparison.md"
    out.write_text(comparison(read_rows(results / "rows.csv")), encoding="utf-8")
    return out
