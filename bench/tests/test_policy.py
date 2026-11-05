from __future__ import annotations

import pytest

from driver.policy import FREE_TEXT_REPLY, RULES, Answer, Question, answer, prose_answer


def ask(*labels: str, multi: bool = False) -> Question:
    return Question(header="H", text="Q?", labels=labels, multi_select=multi)


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("Approve", "Request Changes"), Answer("approve", "Approve")),
        (("Approve", "Request Changes", "Accept as-is"), Answer("approve", "Approve")),
        (("Approve Plan", "Request Changes", "I'll edit the files"), Answer("approve", "Approve Plan")),
        (("Approve all", "Request Changes", "I'll edit the files"), Answer("approve", "Approve all")),
        (("Approve Plans", "Request Changes"), Answer("approve", "Approve Plans")),
        (("Fix findings", "Override blocking sensors"), Answer("fix_findings", "Fix findings", ("Override blocking sensors",))),
        (("Fix it", "Accept the risk"), Answer("fix_findings", "Fix it", ("Accept the risk",))),
        (("Postgres", "SQLite (Recommended)"), Answer("recommended", "SQLite (Recommended)")),
        (("svc-a", "svc-b"), Answer("free_text", FREE_TEXT_REPLY)),
    ],
)
def test_each_rule_answers_its_question(labels: tuple[str, ...], expected: Answer) -> None:
    assert answer(ask(*labels)) == expected


def test_an_override_is_never_chosen_even_when_it_is_recommended_or_the_only_choice() -> None:
    assert answer(ask("Override blocking sensors (Recommended)", "Fix findings")) == Answer(
        "fix_findings", "Fix findings", ("Override blocking sensors (Recommended)",)
    )
    assert answer(ask("Accept the risk (Recommended)", "Keep the finding open")) == Answer(
        "free_text", FREE_TEXT_REPLY, ("Accept the risk (Recommended)",)
    )


def test_fixing_findings_wins_over_approving() -> None:
    assert answer(ask("Approve", "Fix findings")).rule == "fix_findings"


def test_approving_wins_over_a_recommended_option() -> None:
    assert answer(ask("Request Changes (Recommended)", "Approve")).value == "Approve"


def test_a_park_or_partial_approval_is_not_a_plain_approval() -> None:
    assert answer(ask("Approve, but let's stop there for today", "Request Changes")).rule == "free_text"


def test_labels_match_without_case_or_the_recommended_suffix() -> None:
    assert answer(ask("approve (Recommended)", "Request Changes")).value == "approve (Recommended)"


def test_a_multi_select_question_gets_every_recommended_option_and_free_text_stays_text() -> None:
    assert answer(ask("A (Recommended)", "B", "C (Recommended)", multi=True)) == Answer(
        "recommended", ["A (Recommended)", "C (Recommended)"]
    )
    assert answer(ask("A", "B", multi=True)) == Answer("free_text", FREE_TEXT_REPLY)


def test_a_prose_turn_approves_only_a_stage_waiting_at_its_gate() -> None:
    assert prose_answer("requirements-analysis") == Answer("approve", "Approve")
    assert prose_answer(None) == Answer("free_text", FREE_TEXT_REPLY)


def test_the_table_is_ordered_as_the_protocol_states() -> None:
    assert [rule.id for rule in RULES] == [
        "override_offered_and_refused",
        "fix_findings",
        "approve",
        "recommended",
        "free_text",
    ]


def test_a_question_parses_from_the_tool_input_shape() -> None:
    parsed = Question.parse(
        {"header": "Approval", "question": "Go?", "multiSelect": True, "options": [{"label": "Approve", "description": "x"}]}
    )
    assert parsed == Question(header="Approval", text="Go?", labels=("Approve",), multi_select=True)
    assert Question.parse("not a question") == Question(header="", text="", labels=(), multi_select=False)
