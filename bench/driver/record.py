"""The driver's artifacts in --out-dir: answers.jsonl, permissions.jsonl, summary.json."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from driver.aidlc import Workflow
from driver.decide import Finish
from driver.policy import Answer, Question
from driver.usage import Usage

GATE_STATS = ("approve", "fix_findings", "recommended", "free_text", "override_offered_and_refused", "prose_nudges")
PROSE_EXCERPT_CHARS = 2000


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class Record:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.answers = out_dir / "answers.jsonl"
        self.permissions = out_dir / "permissions.jsonl"
        for path in (self.answers, self.permissions):
            path.write_text("", encoding="utf-8")
        self.gates = Counter(dict.fromkeys(GATE_STATS, 0))
        self.denials: Counter[str] = Counter()

    def question(self, question: Question, answer: Answer) -> None:
        self._count(answer)
        _append(
            self.answers,
            {
                "time": _now(),
                "kind": "ask_user_question",
                "header": question.header,
                "question": question.text,
                "options": list(question.labels),
                "multi_select": question.multi_select,
                "answer": answer.value,
                "rule": answer.rule,
                "refused": list(answer.refused),
            },
        )

    def prose(self, agent_text: str, awaiting_stage: str | None, answer: Answer) -> None:
        self._count(answer)
        self.gates["prose_nudges"] += 1
        _append(
            self.answers,
            {
                "time": _now(),
                "kind": "prose_turn",
                "header": None,
                "question": agent_text[-PROSE_EXCERPT_CHARS:],
                "options": [],
                "answer": answer.value,
                "rule": answer.rule,
                "awaiting_stage": awaiting_stage,
            },
        )

    def denial(self, tool_name: str, reason: str | None) -> None:
        self.denials[tool_name] += 1
        _append(self.permissions, {"time": _now(), "tool": tool_name, "decision": "deny", "reason": reason})

    def _count(self, answer: Answer) -> None:
        self.gates[answer.rule] += 1
        if answer.refused:
            self.gates["override_offered_and_refused"] += 1

    def summary(
        self,
        finish: Finish,
        wall_seconds: float,
        usage: Usage,
        workflow: Workflow,
        model_refusals: dict,
        error: str | None,
    ) -> dict:
        return {
            "status": str(finish.status),
            "reason": finish.reason,
            "wall_seconds": round(wall_seconds, 3),
            "total_cost_usd": usage.total_cost_usd,
            "num_turns": usage.num_turns,
            "usage": usage.tokens,
            "models": usage.models,
            "results": usage.results,
            "gate_stats": {name: self.gates[name] for name in GATE_STATS},
            "permission_denials": dict(self.denials),
            "model_refusals": model_refusals,
            "aidlc": {
                "detected": workflow.detected,
                "completed": workflow.complete,
                "final_state_excerpt": workflow.excerpt,
            },
            "error": error,
        }

    def write_summary(self, summary: dict) -> None:
        path = self.out_dir / "summary.json"
        partial = path.with_suffix(".json.partial")
        partial.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(partial, path)
