from __future__ import annotations

from driver.aidlc import Workflow
from driver.decide import Finish, Say, Stall, Status, decide
from driver.policy import FREE_TEXT_REPLY

STATE = """# AI-DLC State

- **Status**: Running
- **Current Stage**: requirements-analysis
- **Next Action**: Execute Requirements Analysis

## Stage Progress
- [x] workspace-detection
- [?] requirements-analysis
- [ ] units-generation
"""


def test_the_probe_output_parses_into_install_and_state() -> None:
    assert Workflow.parse("absent\n") == Workflow(installed=False, state=None)
    assert Workflow.parse("installed\n") == Workflow(installed=True, state=None)
    parsed = Workflow.parse("installed\n" + STATE)
    assert parsed.state == STATE
    assert parsed.awaiting_stage == "requirements-analysis"
    assert not parsed.complete


def test_completion_is_read_from_the_status_or_next_action_field() -> None:
    assert Workflow(True, STATE.replace("Status**: Running", "Status**: Completed")).complete
    assert Workflow(True, STATE.replace("Execute Requirements Analysis", "Workflow complete")).complete
    assert not Workflow(True, "- **Completed**: 5\n").complete


def test_without_aidlc_the_settled_turn_completes_the_run() -> None:
    assert decide(Workflow(False, None), False, 0, 5) == Finish(Status.COMPLETED, "no_aidlc")


def test_an_installed_workflow_that_has_not_started_gets_the_free_text_reply() -> None:
    decision = decide(Workflow(True, None), False, 0, 5)
    assert isinstance(decision, Say) and decision.answer.value == FREE_TEXT_REPLY


def test_a_stage_at_its_gate_gets_approve_and_a_finished_workflow_completes() -> None:
    decision = decide(Workflow(True, STATE), False, 0, 5)
    assert isinstance(decision, Say) and decision.answer.value == "Approve"
    done = Workflow(True, STATE.replace("Status**: Running", "Status**: Completed"))
    assert decide(done, False, 0, 5) == Finish(Status.COMPLETED, "aidlc_complete")


def test_an_error_result_ends_the_run() -> None:
    assert decide(Workflow(True, STATE), True, 0, 5) == Finish(Status.ERROR, "error_result")


def test_the_run_is_stuck_after_the_limit_of_nudges_on_one_unchanged_state() -> None:
    stall = Stall()
    for _ in range(3):
        assert isinstance(decide(Workflow(True, STATE), False, stall.unchanged(STATE), 3), Say)
        stall.record(STATE)
    assert decide(Workflow(True, STATE), False, stall.unchanged(STATE), 3) == Finish(
        Status.STUCK, "prose_nudges_without_progress"
    )
    moved = STATE.replace("[?] requirements", "[x] requirements")
    assert stall.unchanged(moved) == 0
