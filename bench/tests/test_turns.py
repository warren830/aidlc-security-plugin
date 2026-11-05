from __future__ import annotations

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TaskNotificationMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
    TextBlock,
)

from driver.turns import Phase, Turn


def started(task_id: str, task_type: str = "local_agent") -> TaskStartedMessage:
    return TaskStartedMessage(
        subtype="task_started", data={}, task_id=task_id, description="", uuid="u", session_id="s", task_type=task_type
    )


def notified(task_id: str) -> TaskNotificationMessage:
    return TaskNotificationMessage(
        subtype="task_notification",
        data={},
        task_id=task_id,
        status="completed",
        output_file="",
        summary="",
        uuid="u",
        session_id="s",
    )


def updated(task_id: str, status: str) -> TaskUpdatedMessage:
    return TaskUpdatedMessage(subtype="task_updated", data={}, task_id=task_id, patch={"status": status}, status=status)


def result() -> ResultMessage:
    return ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1, session_id="s")


def lead(text: str = "hi", parent: str | None = None) -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model="m", parent_tool_use_id=parent)


def test_a_result_with_nothing_pending_settles_the_turn() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(lead(), 0)
    turn.observe(result(), 1)
    assert turn.phase is Phase.SETTLED


def test_a_pending_agent_holds_the_turn_until_its_report_and_the_next_result() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(result(), 1)
    assert turn.phase is Phase.WAITING_FOR_TASKS
    turn.tick(1000)
    assert turn.phase is Phase.WAITING_FOR_TASKS
    turn.observe(notified("t1"), 2)
    turn.observe(lead(), 3)
    assert turn.phase is Phase.WORKING
    turn.observe(result(), 4)
    assert turn.phase is Phase.SETTLED


def test_a_report_with_no_following_turn_settles_after_the_wait() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(result(), 1)
    turn.observe(notified("t1"), 2)
    assert turn.phase is Phase.SETTLING
    turn.tick(31)
    assert turn.phase is Phase.SETTLING
    turn.tick(32)
    assert turn.phase is Phase.SETTLED


def test_an_agent_that_finished_inside_the_turn_settles_after_the_wait() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(updated("t1", "completed"), 1)
    turn.observe(result(), 2)
    assert (turn.phase, turn.settle_at) == (Phase.SETTLING, 32)
    turn.tick(32)
    assert turn.phase is Phase.SETTLED
    assert turn.pending == set()


def test_the_lead_resuming_cancels_the_settle_wait() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(updated("t1", "completed"), 1)
    turn.observe(result(), 2)
    turn.observe(lead(), 3)
    turn.tick(100)
    assert turn.phase is Phase.WORKING


def test_a_subagent_message_is_not_the_lead_resuming() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(updated("t1", "completed"), 1)
    turn.observe(result(), 2)
    turn.observe(lead(parent="toolu_task"), 3)
    turn.tick(33)
    assert turn.phase is Phase.SETTLED


def test_only_agent_tasks_are_tracked() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("shell", task_type="local_bash"), 0)
    turn.observe(started("remote", task_type="remote_agent"), 0)
    turn.observe(result(), 1)
    assert turn.phase is Phase.SETTLED


def test_a_running_status_update_does_not_settle_a_task() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(started("t1"), 0)
    turn.observe(updated("t1", "running"), 1)
    turn.observe(result(), 2)
    assert turn.phase is Phase.WAITING_FOR_TASKS


def test_resume_starts_a_new_turn() -> None:
    turn = Turn(settle_seconds=30)
    turn.observe(result(), 1)
    turn.resume()
    assert (turn.phase, turn.result) == (Phase.WORKING, None)
