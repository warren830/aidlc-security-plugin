"""What the scripted person does once a turn has settled."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from driver.aidlc import Workflow
from driver.policy import Answer, prose_answer

STUCK_AFTER = 5


class Status(StrEnum):
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    STUCK = "stuck"
    ERROR = "error"


@dataclass(frozen=True)
class Finish:
    status: Status
    reason: str


@dataclass(frozen=True)
class Say:
    answer: Answer


@dataclass
class Stall:
    """Prose nudges sent while the state file stayed the same."""

    snapshot: str | None = None
    nudges: int = 0

    def unchanged(self, snapshot: str) -> int:
        return self.nudges if snapshot == self.snapshot else 0

    def record(self, snapshot: str) -> None:
        if snapshot == self.snapshot:
            self.nudges += 1
        else:
            self.snapshot, self.nudges = snapshot, 1


def decide(workflow: Workflow, result_is_error: bool, unchanged_nudges: int, stuck_after: int) -> Finish | Say:
    if result_is_error:
        return Finish(Status.ERROR, "error_result")
    if not workflow.detected:
        return Finish(Status.COMPLETED, "no_aidlc")
    if workflow.complete:
        return Finish(Status.COMPLETED, "aidlc_complete")
    if unchanged_nudges >= stuck_after:
        return Finish(Status.STUCK, "prose_nudges_without_progress")
    return Say(prose_answer(workflow.awaiting_stage))
