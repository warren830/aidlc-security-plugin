"""When the agent's turn is over, so that the scripted person may speak.

A result frame ends one turn, not the session: a subagent still running wakes
the lead for another turn when it reports. The rule is the one aidlc-workflows'
own SDK driver uses (tests/harness/sdk-drive.ts, header and trackDriveTask):
a task is pending from task_started until its task_notification, a
task_updated with a finished status marks it settled, and a result whose
pending tasks have all settled waits briefly for a report before it counts as
the end of the turn. Only agent tasks are tracked, as in the SDK
(_internal/query.py DEFERRING_TASK_TYPES): a background shell such as a dev
server may never finish, and tracking it would hold the turn open until the
timeout.

Background shells are still counted, for one case: in an AI-DLC run the agent
waits on a slow job (a Security Agent review takes 5 to 30 minutes) by
starting `sleep 240` in the background and ending its turn, and the shell's
notification wakes it. A person would let it be. So the session may ask the
turn to wait for its live shells, up to a limit, before the person speaks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TaskNotificationMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
    UserMessage,
)

AGENT_TASK_TYPES = frozenset({"local_agent", "local_workflow"})
SHELL_TASK_TYPES = frozenset({"local_bash"})
FINISHED_STATUSES = frozenset({"completed", "failed", "killed", "stopped"})
SETTLE_SECONDS = 30.0
SHELL_WAIT_SECONDS = 900.0


class Phase(Enum):
    WORKING = "working"
    WAITING_FOR_TASKS = "waiting_for_tasks"
    WAITING_FOR_SHELLS = "waiting_for_shells"
    SETTLING = "settling"
    SETTLED = "settled"


@dataclass
class Turn:
    settle_seconds: float = SETTLE_SECONDS
    phase: Phase = Phase.WORKING
    pending: set[str] = field(default_factory=set)
    finished: set[str] = field(default_factory=set)
    shells: set[str] = field(default_factory=set)
    settle_at: float | None = None
    result: ResultMessage | None = None

    def resume(self) -> None:
        """The person spoke: a new turn is under way."""
        self.phase, self.settle_at, self.result = Phase.WORKING, None, None

    def wait_for_shells(self, now: float, seconds: float) -> None:
        """Hold the settled turn until a live background shell reports, or for `seconds`."""
        self.phase, self.settle_at = Phase.WAITING_FOR_SHELLS, now + seconds

    def observe(self, message: object, now: float) -> None:
        match message:
            case TaskStartedMessage(task_id=task_id, task_type=task_type) if task_type in SHELL_TASK_TYPES:
                self.shells.add(task_id)
            case TaskStartedMessage(task_id=task_id, task_type=task_type) if task_type in AGENT_TASK_TYPES:
                self.pending.add(task_id)
                self._work()
            case TaskNotificationMessage(task_id=task_id):
                self.pending.discard(task_id)
                self.finished.discard(task_id)
                self.shells.discard(task_id)
                self._task_moved(now)
            case TaskUpdatedMessage(task_id=task_id, status=status) if (
                status in FINISHED_STATUSES and task_id in self.pending
            ):
                self.finished.add(task_id)
                self._task_moved(now)
            case AssistantMessage(parent_tool_use_id=None) | UserMessage(parent_tool_use_id=None):
                self._work()
            case ResultMessage():
                self.result = message
                if not self.pending:
                    self.phase = Phase.SETTLED
                elif self.pending <= self.finished:
                    self._settle_from(now)
                else:
                    self.phase = Phase.WAITING_FOR_TASKS

    def tick(self, now: float) -> None:
        if self.phase is Phase.WAITING_FOR_SHELLS and self.settle_at is not None and now >= self.settle_at:
            self.shells.clear()
            self.phase = Phase.SETTLED
        if self.phase is Phase.SETTLING and self.settle_at is not None and now >= self.settle_at:
            self.pending.clear()
            self.finished.clear()
            self.phase = Phase.SETTLED

    def _work(self) -> None:
        self.phase, self.settle_at = Phase.WORKING, None

    def _task_moved(self, now: float) -> None:
        if self.phase is Phase.WAITING_FOR_SHELLS:
            if not self.shells:
                self._settle_from(now)
            return
        if self.phase in (Phase.WAITING_FOR_TASKS, Phase.SETTLING) and self.pending <= self.finished:
            self._settle_from(now)

    def _settle_from(self, now: float) -> None:
        self.phase, self.settle_at = Phase.SETTLING, now + self.settle_seconds
