"""The three arms: the only things that differ between them.

An arm is the setup that runs in its container and the first message that
starts its work. AI-DLC needs its entry command, so arms 2 and 3 open with
/aidlc; arm 1 sends the prompt as it is, as `claude -p` would. Everything
else (Claude Code version, model, timeout, tools, driver, patch collection)
comes from config.env and is the same for every arm.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

SETUP = Path(__file__).resolve().parent / "setup"
AIDLC_ENTRY = "/aidlc --scope classic --project-type {project_type} {prompt}"


@dataclass(frozen=True)
class Arm:
    label: str
    setup_parts: tuple[str, ...]
    first_message: str

    def setup_script(self) -> str:
        """One self-contained script: the runner copies a single file into the container."""
        parts = "".join(f"\n# --- bench/setup/{part}\n{(SETUP / part).read_text(encoding='utf-8')}" for part in self.setup_parts)
        return f"#!/usr/bin/env bash\n# Container setup for {self.label}.\nset -euo pipefail\n{parts}"

    def first_message_template(self, project_type: str) -> str:
        return self.first_message.replace("{project_type}", project_type)


ARMS: dict[str, Arm] = {
    arm.label: arm
    for arm in (
        Arm("arm1", ("common.sh",), "{prompt}"),
        Arm("arm2", ("common.sh", "aidlc.sh"), AIDLC_ENTRY),
        Arm("arm3", ("common.sh", "aidlc.sh", "security.sh"), AIDLC_ENTRY),
    )
}

# The fields an arm may vary; a new field is a new difference between arms.
VARYING = ("label", "setup_parts", "first_message")
assert tuple(field.name for field in fields(Arm)) == VARYING


def write_setup_script(arm: Arm, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(arm.setup_script(), encoding="utf-8")
    path.chmod(0o755)
    return path
