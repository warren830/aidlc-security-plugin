"""How the driver reaches `claude`: a generated wrapper the SDK runs as its CLI.

The wrapper tees the CLI's stdout to raw.jsonl and keeps the CLI's exit
status: it execs the CLI, so the process the SDK signals and waits for is the
CLI itself (or `docker exec`), and only tee runs beside it.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from driver.aidlc import PROBE

# The variables the SDK sets for its CLI subprocess
# (SubprocessCLITransport.connect): the docker transport forwards these names,
# never the host's other variables and never a value on the command line.
SDK_ENV_NAMES = (
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_AGENT_SDK_VERSION",
    "CLAUDE_CODE_SDK_READS_SESSION_STATE",
)


def _sourcing(sources: tuple[str, ...]) -> str:
    """Shell that sources each file that exists, its stdout kept off the CLI's stream."""
    return "".join(f"[ -f {shlex.quote(path)} ] && . {shlex.quote(path)} >&2; " for path in sources)


def _tee(raw: Path) -> str:
    return f"> >(exec tee -a {shlex.quote(str(raw))})"


@dataclass(frozen=True)
class DockerTransport:
    container: str
    workdir: str
    sources: tuple[str, ...]

    cwd = None

    def wrapper(self, raw: Path) -> str:
        inner = _sourcing(self.sources) + 'exec claude "$@"'
        forwarded = " ".join(f"-e {name}" for name in SDK_ENV_NAMES)
        return (
            "#!/usr/bin/env bash\n"
            f"exec docker exec -i -w {shlex.quote(self.workdir)} {forwarded} {shlex.quote(self.container)} "
            f'bash -c {shlex.quote(inner)} _ "$@" {_tee(raw)}\n'
        )

    def probe(self) -> list[str]:
        return ["docker", "exec", "-w", self.workdir, self.container, "sh", "-c", PROBE]


@dataclass(frozen=True)
class LocalTransport:
    cwd: Path
    claude_bin: str
    sources: tuple[str, ...]

    def wrapper(self, raw: Path) -> str:
        return (
            "#!/usr/bin/env bash\n"
            f"{_sourcing(self.sources)}\n"
            f'exec {shlex.quote(self.claude_bin)} "$@" {_tee(raw)}\n'
        )

    def probe(self) -> list[str]:
        return ["sh", "-c", PROBE]


Transport = DockerTransport | LocalTransport


def write_wrapper(transport: Transport, out_dir: Path) -> Path:
    raw = out_dir / "raw.jsonl"
    raw.write_text("", encoding="utf-8")
    path = out_dir / "claude-cli.sh"
    path.write_text(transport.wrapper(raw.resolve()), encoding="utf-8")
    path.chmod(0o755)
    return path
