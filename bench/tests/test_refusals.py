import json
from pathlib import Path

from driver.refusals import scan, scan_file


def frames(*items: dict) -> list[str]:
    return [json.dumps(item) for item in items]


def assistant(stop: str | None, parent: str | None = None) -> dict:
    return {"type": "assistant", "parent_tool_use_id": parent, "message": {"stop_reason": stop, "content": []}}


def test_a_run_with_no_stop_reports_zero_and_not_stopped() -> None:
    found = scan(frames(assistant("end_turn"), {"type": "result", "stop_reason": "end_turn", "safety_stops": 0}))
    assert found["safety_stops"] == 0
    assert found["stopped_by_model"] is False
    assert found["ended_on_refusal"] is False


def test_safety_stops_are_running_totals_and_a_drop_starts_a_new_segment() -> None:
    found = scan(frames(
        {"type": "result", "safety_stops": 1},
        {"type": "result", "safety_stops": 2},
        {"type": "result", "safety_stops": 0},
        {"type": "result", "safety_stops": 1},
    ))
    assert found["safety_stops"] == 3
    assert found["stopped_by_model"] is True


def test_a_refusal_that_ends_the_main_thread_is_flagged() -> None:
    found = scan(frames(
        assistant("tool_use"),
        {"type": "system", "subtype": "model_refusal_no_fallback", "original_model": "m"},
        assistant("refusal"),
    ))
    assert found["refusal_stop_reasons"] == 1
    assert found["events"]["model_refusal_no_fallback"] == 1
    assert found["ended_on_refusal"] is True


def test_a_subagents_refusal_counts_but_does_not_end_the_run() -> None:
    found = scan(frames(assistant("refusal", parent="toolu_1"), assistant("end_turn")))
    assert found["stopped_by_model"] is True
    assert found["ended_on_refusal"] is False


def test_another_model_answering_is_counted_as_its_own_event() -> None:
    found = scan(frames({"type": "system", "subtype": "model_refusal_fallback", "fallback_model": "x"}))
    assert found["events"]["model_refusal_fallback"] == 1


def test_lines_that_are_not_frames_are_skipped(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    raw.write_text("not json\n[1, 2]\n" + frames(assistant("refusal"))[0] + "\n", encoding="utf-8")
    assert scan_file(raw)["ended_on_refusal"] is True
    assert scan_file(tmp_path / "missing.jsonl")["safety_stops"] == 0
