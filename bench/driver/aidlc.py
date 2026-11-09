"""What the AI-DLC install and state file in the project say about the workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass

# The orchestrator skill a Claude Code install of AI-DLC writes
# (harness/claude/manifest.ts orchestratorSkillPath).
INSTALL_MARKER = ".claude/skills/aidlc/SKILL.md"

# One shell snippet for both transports: the first line says whether AI-DLC is
# installed, the rest is the newest intent's state file. A benchmark run holds
# one intent, so the newest state file is the active one.
PROBE = (
    f"if [ -f {INSTALL_MARKER} ]; then echo installed; else echo absent; fi; "
    "state=$(ls -t aidlc/spaces/*/intents/*/aidlc-state.md 2>/dev/null | head -n 1); "
    'if [ -n "$state" ]; then cat "$state"; fi'
)

_AWAITING = re.compile(r"^- \[\?\] ([a-z0-9-]+)", re.MULTILINE)
EXCERPT_CHARS = 4000


def state_field(text: str, name: str) -> str | None:
    match = re.search(rf"^- \*\*{re.escape(name)}\*\*:[ \t]*(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


@dataclass(frozen=True)
class Workflow:
    installed: bool
    state: str | None

    @classmethod
    def parse(cls, probe_output: str) -> Workflow:
        marker, _, state = probe_output.partition("\n")
        return cls(installed=marker.strip() == "installed", state=state if state.strip() else None)

    @property
    def detected(self) -> bool:
        return self.installed or self.state is not None

    @property
    def complete(self) -> bool:
        if self.state is None:
            return False
        return (
            state_field(self.state, "Status") == "Completed"
            or state_field(self.state, "Next Action") == "Workflow complete"
        )

    @property
    def awaiting_stage(self) -> str | None:
        """The stage whose approval gate is open (`[?]` in the stage list)."""
        match = _AWAITING.search(self.state or "")
        return match.group(1) if match else None

    @property
    def snapshot(self) -> str:
        return self.state or ""

    @property
    def excerpt(self) -> str:
        return (self.state or "")[:EXCERPT_CHARS]


NO_PROBE = Workflow(installed=False, state=None)
