"""The scripted person's answers: one ordered rule table, first match wins."""

from __future__ import annotations

from dataclasses import dataclass

# The pre-registered design's fixed reply to a question ("按你的推荐"), in
# English because every prompt the agent sees is English.
FREE_TEXT_REPLY = "Go with your recommendation."
PROSE_APPROVAL = "Approve"
RECOMMENDED_SUFFIX = "(Recommended)"


def plain(label: str) -> str:
    """A label as the rules compare it: no "(Recommended)" suffix, case-folded."""
    text = label.strip()
    if text.endswith(RECOMMENDED_SUFFIX):
        text = text[: -len(RECOMMENDED_SUFFIX)]
    return text.strip().casefold()


@dataclass(frozen=True)
class Rule:
    id: str
    refuse: frozenset[str] = frozenset()
    pick: frozenset[str] = frozenset()
    pick_recommended: bool = False
    reply: str | None = None

    def choose(self, offered: list[str]) -> list[str]:
        if self.reply is not None:
            return [self.reply]
        if self.pick_recommended:
            return [label for label in offered if label.strip().endswith(RECOMMENDED_SUFFIX)]
        return [label for label in offered if plain(label) in self.pick]


RULES: tuple[Rule, ...] = (
    Rule("override_offered_and_refused", refuse=frozenset({"override blocking sensors", "accept the risk"})),
    Rule("fix_findings", pick=frozenset({"fix findings", "fix it"})),
    # AI-DLC's approval choices: the stage gate, then Code Generation's plan
    # approval for one Unit, a batch, and a group (aidlc-plan-approval-ask.ts).
    Rule("approve", pick=frozenset({"approve", "approve plan", "approve plans", "approve all"})),
    Rule("recommended", pick_recommended=True),
    Rule("free_text", reply=FREE_TEXT_REPLY),
)

REFUSED = frozenset().union(*(rule.refuse for rule in RULES))


@dataclass(frozen=True)
class Question:
    header: str
    text: str
    labels: tuple[str, ...]
    multi_select: bool

    @classmethod
    def parse(cls, item: object) -> Question:
        item = item if isinstance(item, dict) else {}
        options = item.get("options") if isinstance(item.get("options"), list) else []
        labels = tuple(
            str(option.get("label", "")) if isinstance(option, dict) else str(option) for option in options
        )
        return cls(
            header=str(item.get("header") or ""),
            text=str(item.get("question") or ""),
            labels=labels,
            multi_select=bool(item.get("multiSelect")),
        )


@dataclass(frozen=True)
class Answer:
    rule: str
    value: str | list[str]
    refused: tuple[str, ...] = ()


def answer(question: Question) -> Answer:
    refused = tuple(label for label in question.labels if plain(label) in REFUSED)
    offered = [label for label in question.labels if label not in refused]
    for rule in RULES:
        chosen = rule.choose(offered)
        if not chosen:
            continue
        if rule.reply is not None or not question.multi_select:
            return Answer(rule.id, chosen[0], refused)
        return Answer(rule.id, chosen, refused)
    raise AssertionError("the free_text rule always answers")


def prose_answer(awaiting_stage: str | None) -> Answer:
    """A turn that ended in prose: approve a stage that waits at its gate, else the fixed reply."""
    if awaiting_stage is not None:
        return Answer("approve", PROSE_APPROVAL)
    return Answer("free_text", FREE_TEXT_REPLY)
