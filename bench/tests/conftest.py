from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BENCH = TESTS.parent
sys.path.insert(0, str(BENCH))

FAKE_CLAUDE = TESTS / "fake_claude.py"
FAKE_DOCKER = TESTS / "fake_docker.py"
AIDLC_SKILL = ".claude/skills/aidlc/SKILL.md"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass
class DriverRun:
    code: int
    stderr: str
    out: Path
    project: Path

    @property
    def summary(self) -> dict:
        return json.loads((self.out / "summary.json").read_text(encoding="utf-8"))

    @property
    def answers(self) -> list[dict]:
        return read_jsonl(self.out / "answers.jsonl")

    @property
    def fake_log(self) -> list[dict]:
        return read_jsonl(self.project / ".fake-claude" / "log.jsonl")

    @property
    def user_messages(self) -> list:
        return [entry["content"] for entry in self.fake_log if entry["event"] == "user"]

    @property
    def permissions(self) -> list[dict]:
        return [entry for entry in self.fake_log if entry["event"] == "permission"]

    @property
    def fake_start(self) -> dict:
        return next(entry for entry in self.fake_log if entry["event"] == "start")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    (path / ".fake-claude").mkdir(parents=True)
    return path


def scenario(project: Path, *turns: list[dict]) -> None:
    (project / ".fake-claude" / "scenario.json").write_text(json.dumps({"turns": list(turns)}), encoding="utf-8")


def install_aidlc(project: Path) -> None:
    skill = project / AIDLC_SKILL
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: aidlc\n---\n", encoding="utf-8")


def state(stage_line: str, status: str = "Running") -> str:
    return f"# State\n\n- **Status**: {status}\n- **Current Stage**: requirements-analysis\n\n## Stages\n{stage_line}\n"


STATE_PATH = "aidlc/spaces/default/intents/demo-1a2b3c4d/aidlc-state.md"


def run_driver(
    project: Path,
    *args: str,
    prompt: str = "Build the feature.",
    env: dict[str, str] | None = None,
    timeout: float = 90,
    local: bool = True,
) -> DriverRun:
    out = project.parent / "out"
    prompt_file = project.parent / "prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    command = [sys.executable, str(BENCH / "bench.py"), "driver", "--prompt-file", str(prompt_file), "--out-dir", str(out)]
    if local:
        command += ["--local-cwd", str(project), "--claude-bin", str(FAKE_CLAUDE)]
    command += ["--settle-seconds", "0.5", *args]
    run_env = {**os.environ, **(env or {})}
    done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=run_env)
    return DriverRun(code=done.returncode, stderr=done.stderr, out=out, project=project)
