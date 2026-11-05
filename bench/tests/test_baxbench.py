from __future__ import annotations

import collections
import io
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath

import pytest

from arms import ARMS
from baxbench import runner, sampler
from conftest import BENCH, TESTS, read_jsonl

EXPORT = TESTS / "baxbench_export_sample.json"
PILOT = BENCH / "baxbench" / "pilot_tasks.json"


def task(scenario: str, env: str) -> runner.Task:
    return runner.load_tasks(EXPORT, [{"scenario": scenario, "env": env}])[0]


def test_the_pilot_sample_is_the_committed_one_and_meets_its_rule() -> None:
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    assert pilot["baxbench_ref"] == "v1.0.0"
    assert (len(pilot["scenarios"]), len(pilot["envs"])) == (28, 14)
    assert pilot["tasks"] == sampler.sample(pilot["scenarios"], pilot["envs"], seed=pilot["seed"])
    pairs = [(t["scenario"], t["env"]) for t in pilot["tasks"]]
    assert len(pairs) == len(set(pairs)) == 40
    per_scenario = collections.Counter(s for s, _ in pairs)
    assert set(per_scenario) == set(pilot["scenarios"])
    assert max(per_scenario.values()) == 2
    per_env = collections.Counter(e for _, e in pairs)
    assert set(per_env) == set(pilot["envs"])
    assert max(per_env.values()) - min(per_env.values()) <= 1


def test_the_sample_is_deterministic_and_depends_on_the_seed() -> None:
    scenarios = [f"s{i}" for i in range(28)]
    envs = [f"e{i}" for i in range(14)]
    assert sampler.sample(scenarios, envs) == sampler.sample(list(reversed(scenarios)), envs)
    assert sampler.sample(scenarios, envs, seed=1) != sampler.sample(scenarios, envs, seed=2)
    with pytest.raises(ValueError):
        sampler.sample(scenarios[:10], envs)


def test_results_land_where_baxbench_test_mode_reads_them() -> None:
    assert runner.code_dir(Path("results"), "arm2", task("Calculator", "Go-net/http")) == Path(
        "results/arm2/Calculator/Go-net-http/temp0.2-openapi-none/sample0/code"
    )


def test_the_copy_drops_workflow_files_and_build_output(tmp_path: Path) -> None:
    source = tmp_path / "code"
    for name in ("app.py", "lib/util.py", "node_modules/x/index.js", "lib/__pycache__/u.pyc", "target/debug/app",
                 ".venv/bin/python", "aidlc-docs/plan.md", ".aidlc-security.json", ".claude/settings.json",
                 "CLAUDE.md", "AGENTS.md", ".mcp.json", ".git/HEAD"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    copied = runner.copy_code(source, tmp_path / "out")
    kept = sorted(p.relative_to(tmp_path / "out").as_posix() for p in (tmp_path / "out").rglob("*") if p.is_file())
    assert kept == ["app.py", "lib/util.py"]
    assert copied == 2
    assert runner.kept(PurePosixPath("src/aidlc_helper.py"))
    assert not runner.kept(PurePosixPath("web/node_modules/a.js"))


def test_the_agent_image_is_the_env_dockerfile_with_no_app() -> None:
    rust = runner.image_context(task("Calculator", "Rust-Actix"))
    assert rust["main.rs"] == ""
    assert "Cargo.toml" in rust
    assert rust["Dockerfile"].startswith(task("Calculator", "Rust-Actix").dockerfile.rstrip())
    assert runner.AGENT_IMAGE_TOOLS in rust["Dockerfile"]
    flask = runner.image_context(task("Login", "Python-Flask"))
    assert sorted(flask) == ["Dockerfile", "requirements.txt"]
    go = runner.image_context(task("Calculator", "Go-net/http"))
    assert sorted(go) == ["Dockerfile", "build_helper.go", "go.mod"]
    with tarfile.open(fileobj=io.BytesIO(runner.context_tar(rust))) as tar:
        assert sorted(tar.getnames()) == sorted(rust)
    tag = runner.image_tag(task("Calculator", "Go-net/http"), go)
    assert tag.startswith("bench-agent-go-net-http:") and tag == tag.lower()


def test_one_baxbench_call_per_env_names_exactly_the_sampled_tasks(tmp_path: Path) -> None:
    tasks = [task("Calculator", "Go-net/http"), task("Calculator", "Rust-Actix"), task("Login", "Python-Flask")]
    assert runner.by_env(tasks) == {"Go-net/http": ["Calculator"], "Python-Flask": ["Login"], "Rust-Actix": ["Calculator"]}
    argv = runner.test_argv("py", tmp_path, "arm1", "Go-net/http", ["Calculator"], "test", 8)
    assert argv[argv.index("--envs") + 1] == "Go-net/http"
    assert argv[argv.index("--models") + 1] == "arm1"
    assert argv[argv.index("--temperature") + 1] == "0.2"
    assert argv[argv.index("--safety_prompt") + 1] == "none"


def test_the_container_runs_on_the_host_network_and_stays_up() -> None:
    name = runner.container_name("arm3", task("Calculator", "Go-net/http"))
    assert name.startswith("bench-arm3-calculator-go-net-http-")
    assert runner.run_argv(name, "img:1") == [
        "docker", "run", "-d", "--name", name, "--network", "host", "--entrypoint", "tail", "img:1", "-f", "/dev/null",
    ]


@pytest.fixture
def fake_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").symlink_to(TESTS / "fake_docker_runner.py")
    log = tmp_path / "docker.jsonl"
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("FAKE_DOCKER_LOG", str(log))
    monkeypatch.setenv("FAKE_DOCKER_STATE", str(tmp_path / "docker-state"))
    return log


def context(tmp_path: Path, arm: str = "arm3") -> runner.Context:
    pins = {
        "CLAUDE_CODE_VERSION": "2.1.318",
        "TIMEOUT_SECONDS": "60",
        "ALLOWED_TOOLS": "Bash,Edit",
        "DISALLOWED_TOOLS": "mcp__security-agent__setup",
    }
    environ = {"ANTHROPIC_MODEL": "model-x", "AWS_REGION": "us-east-1", "HOST_ONLY_SECRET": "s3cr3t"}
    setup = tmp_path / "setup.sh"
    setup.write_text("#!/bin/sh\n", encoding="utf-8")
    return runner.Context(
        arm=ARMS[arm],
        results=tmp_path / "results",
        artifacts=tmp_path / "artifacts",
        setup_script=setup,
        assets=tmp_path / "assets",
        pins=pins,
        environ=environ,
    )


def stub_driver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    calls = tmp_path / "driver-calls.jsonl"
    script = f"import json, sys; open({str(calls)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')"
    real = runner.driver_argv

    def argv(ctx: runner.Context, container: str, t: runner.Task, out: Path) -> list[str]:
        return [sys.executable, "-c", script, *real(ctx, container, t, out)[3:]]

    monkeypatch.setattr(runner, "driver_argv", argv)
    return calls


def test_a_task_runs_setup_and_the_driver_then_hands_baxbench_the_app(fake_docker: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = stub_driver(monkeypatch, tmp_path)
    ctx = context(tmp_path)
    rust = task("Calculator", "Rust-Actix")

    record = runner.run_task(ctx, rust)

    assert record["setup_ok"] and record["driver_exit"] == 0, record
    docker = read_jsonl(fake_docker)
    verbs = [call["argv"][0] if call["argv"][0] != "image" else "inspect" for call in docker]
    assert verbs == ["inspect", "build", "run", "exec", "cp", "cp", "exec", "exec", "exec", "exec", "cp", "rm"]
    env_files = [call["stdin"] for call in docker if call["argv"][0] == "exec" and "-i" in call["argv"]]
    assert "export BENCH_PROJECT_DIR=/app" in env_files[0]
    assert "ANTHROPIC_MODEL" not in env_files[0]
    assert "export ANTHROPIC_MODEL=model-x" in env_files[1]
    assert "export CLAUDE_CODE_MAX_OUTPUT_TOKENS=50000" in env_files[1]
    assert "s3cr3t" not in json.dumps(docker)
    assert "model-x" not in json.dumps([call["argv"] for call in docker])
    driver = read_jsonl(calls)[0]
    assert driver[driver.index("--workdir") + 1] == "/app"
    assert driver[driver.index("--first-message-template") + 1] == "/aidlc --scope classic --project-type greenfield {prompt}"
    assert [driver[i + 1] for i, arg in enumerate(driver) if arg == "--source"] == list(runner.SOURCES)
    code = runner.code_dir(ctx.results, "arm3", rust)
    assert sorted(p.relative_to(code).as_posix() for p in code.rglob("*") if p.is_file()) == ["src/main.rs"]
    assert record["code_files"] == 1
    saved = json.loads((ctx.artifacts / "arm3" / "Calculator" / "Rust-Actix" / "task.json").read_text(encoding="utf-8"))
    assert saved["ended"] and saved["image"].startswith("bench-agent-rust-actix:")

    again = runner.run_task(ctx, rust)
    assert again == saved
    assert len(read_jsonl(fake_docker)) == len(docker)


def test_a_failed_setup_skips_the_driver_and_still_gives_baxbench_a_code_dir(fake_docker: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = stub_driver(monkeypatch, tmp_path)
    monkeypatch.setenv("FAKE_SETUP_FAILS", "1")
    ctx = context(tmp_path)

    record = runner.run_task(ctx, task("Login", "Python-Flask"))

    assert record["setup_ok"] is False
    assert record["error"] == "setup exited 9"
    assert not calls.exists()
    assert "setup broke" in (ctx.artifacts / "arm3" / "Login" / "Python-Flask" / "setup.log").read_text(encoding="utf-8")
    assert runner.code_dir(ctx.results, "arm3", task("Login", "Python-Flask")).is_dir()
