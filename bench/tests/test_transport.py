from __future__ import annotations

import subprocess
from pathlib import Path

from driver.transport import SDK_ENV_NAMES, DockerTransport, LocalTransport, write_wrapper


def test_the_docker_wrapper_forwards_names_only_and_sources_in_order(tmp_path: Path) -> None:
    transport = DockerTransport(container="c 1", workdir="/project", sources=("/root/.claude_env", "/root/.bench_agent_env"))
    path = write_wrapper(transport, tmp_path)
    script = path.read_text(encoding="utf-8")

    assert subprocess.run(["bash", "-n", str(path)], check=False).returncode == 0
    assert all(f"-e {name} " in script for name in SDK_ENV_NAMES)
    assert "=" not in script.split("docker exec", 1)[1].split("bash -c", 1)[0]
    assert script.index("/root/.claude_env") < script.index("/root/.bench_agent_env")
    assert "'c 1'" in script
    assert (tmp_path / "raw.jsonl").read_text() == ""


def test_the_local_wrapper_keeps_the_exit_status_and_tees_stdout(tmp_path: Path) -> None:
    fake = tmp_path / "fake claude"
    fake.write_text('#!/bin/sh\necho "{\\"argv\\": \\"$*\\"}"\nexit 7\n', encoding="utf-8")
    fake.chmod(0o755)
    env_file = tmp_path / "env.sh"
    env_file.write_text("echo noise-from-env-file\n", encoding="utf-8")
    transport = LocalTransport(cwd=tmp_path, claude_bin=str(fake), sources=(str(env_file),))
    path = write_wrapper(transport, tmp_path)

    done = subprocess.run([str(path), "--a", "b c"], capture_output=True, text=True, check=False)

    assert done.returncode == 7
    assert done.stdout == '{"argv": "--a b c"}\n'
    assert "noise-from-env-file" in done.stderr
    raw = tmp_path / "raw.jsonl"
    for _ in range(50):
        if raw.read_text():
            break
        subprocess.run(["sleep", "0.05"], check=True)
    assert raw.read_text() == done.stdout


def test_the_state_probe_runs_in_the_work_dir() -> None:
    docker = DockerTransport(container="c", workdir="/app", sources=())
    assert docker.probe()[:5] == ["docker", "exec", "-w", "/app", "c"]
    assert LocalTransport(cwd=Path("/x"), claude_bin="claude", sources=()).probe()[:2] == ["sh", "-c"]
