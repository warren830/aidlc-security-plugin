"""The scripted person at the SDK's permission callback."""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from driver.decide import Finish, Status
from driver.policy import Question, answer
from driver.record import Record

ASK_TOOL = "AskUserQuestion"


class Person:
    """Answers AskUserQuestion by the rule table and denies every other prompt.

    Claude Code asks this callback only for a tool call its allow rules do not
    cover, which `claude -p` denies, so the person denies it too. An identical
    question asked again more than `stuck_after` times in a row ends the run
    as stuck: the agent is not taking the answer, and asking on would run to
    the timeout.
    """

    def __init__(self, record: Record, stuck_after: int) -> None:
        self.record = record
        self.stuck_after = stuck_after
        self.stop: Finish | None = None
        self._last_asked: tuple[str, ...] | None = None
        self._asked_in_a_row = 0

    async def can_use_tool(
        self, tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        if tool_name != ASK_TOOL:
            self.record.denial(tool_name, context.decision_reason)
            return PermissionResultDeny(message=f"Permission to use {tool_name} was denied in this run.")
        questions = [Question.parse(item) for item in tool_input.get("questions") or []]
        asked = tuple(question.text for question in questions)
        self._asked_in_a_row = self._asked_in_a_row + 1 if asked == self._last_asked else 1
        self._last_asked = asked
        if self._asked_in_a_row > self.stuck_after:
            self.stop = Finish(Status.STUCK, "question_reasked")
            return PermissionResultDeny(message="The run stops here.", interrupt=True)
        answers: dict[str, str | list[str]] = {}
        for question in questions:
            chosen = answer(question)
            answers[question.text] = chosen.value
            self.record.question(question, chosen)
        return PermissionResultAllow(updated_input={**tool_input, "answers": answers})
