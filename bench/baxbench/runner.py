"""Run one arm on BaxBench tasks, then BaxBench's own `--mode test` and `--mode evaluate`.

Per task: an agent image from the env's Dockerfile with its dependencies and
no app; a container that stays up, on its own bridge network so that
agents testing on port 5000 at the same time cannot collide; a git baseline in the
work dir (the plugin's diff scan needs a repository); the arm's setup in the
same /opt layout and agent env file as the SusVibes fork's runner
(evaluation_harness/base.py, replicated here because importing it pulls in the
whole susvibes package); the driver; then the app in /app/code, copied into
BaxBench's results layout without workflow files and build output.
"""

from __future__ import annotations

import concurrent.futures
import fnmatch
import hashlib
import io
import json
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pins as pinfile
import runenv
from arms import Arm

BENCH = Path(__file__).resolve().parent.parent
TEMPERATURE = 0.2  # main.py's default; only part of the results path, agents have no temperature
SAMPLE = 0
SPEC = "openapi-none"
CONTAINER_ASSETS = "/opt/bench-assets"
CONTAINER_SETUP = "/opt/setup-env.sh"
AGENT_ENV_FILE = "/root/.bench_agent_env"
# The fork's DockerIntegration.sourced_env_files, in its order.
SOURCES = ("/root/.claude_env", "/root/.nvm/nvm.sh", "/root/.bashrc", AGENT_ENV_FILE)
DRIVER_GRACE_SECONDS = 300
# Build output anywhere in the app; workflow files at its top, as the SusVibes
# patch excludes them (evaluation_harness/base.py PATCH_EXCLUDES).
BUILD_OUTPUT = ("node_modules", "__pycache__", "target", ".venv", ".git")
WORKFLOW_FILES = (".claude", "CLAUDE.md", "AGENTS.md", ".mcp.json", "aidlc*", ".aidlc*")
AGENT_IMAGE_TOOLS = (
    "RUN (command -v git && command -v curl) >/dev/null 2>&1 "
    "|| (apt-get update && apt-get install -y git curl ca-certificates)"
)
BUILD_DIRS_IGNORED = ("node_modules/", "target/", "__pycache__/", ".venv/")


@dataclass(frozen=True)
class Task:
    scenario: str
    env: str
    prompt: str
    dockerfile: str
    workdir: str
    manifest_files: dict[str, str]
    code_filename: str | None

    @property
    def name(self) -> str:
        return f"{self.scenario}/{self.env}"


def load_tasks(export: Path, wanted: list[dict[str, str]]) -> list[Task]:
    by_key = {(t["scenario"], t["env"]): t for t in json.loads(export.read_text(encoding="utf-8"))["tasks"]}
    missing = [w for w in wanted if (w["scenario"], w["env"]) not in by_key]
    if missing:
        raise SystemExit(f"tasks not in the BaxBench export: {missing}")
    return [Task(**by_key[(w["scenario"], w["env"])]) for w in wanted]


def esc(text: str) -> str:
    """BaxBench's own path escaping (src/tasks.py esc)."""
    return text.replace("/", "-")


def sample_dir(results: Path, arm: str, task: Task) -> Path:
    """Task.get_sample_dir in BaxBench's src/tasks.py, for model=arm."""
    return results / esc(arm) / esc(task.scenario) / esc(task.env) / f"temp{float(TEMPERATURE)}-{SPEC}" / f"sample{SAMPLE}"


def code_dir(results: Path, arm: str, task: Task) -> Path:
    return sample_dir(results, arm, task) / "code"


def kept(relative: PurePosixPath) -> bool:
    def matches(name: str, patterns: tuple[str, ...]) -> bool:
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)

    return not matches(relative.parts[0], WORKFLOW_FILES) and not any(matches(part, BUILD_OUTPUT) for part in relative.parts)


def copy_code(source: Path, dest: Path) -> int:
    """Copy the agent's app without workflow files and build output; returns the file count."""
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(source.rglob("*")) if source.is_dir() else []:
        relative = PurePosixPath(path.relative_to(source).as_posix())
        if not kept(relative) or path.is_symlink() or not path.is_file():
            continue
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def named_copy_sources(dockerfile: str) -> list[str]:
    """Files a COPY line names one by one (no glob, not the whole context)."""
    named = []
    for line in dockerfile.splitlines():
        if line.split(None, 1)[:1] != ["COPY"]:
            continue
        words = shlex.split(line, comments=True)
        for source in [word for word in words[1:-1] if not word.startswith("--")]:
            if source not in ("/", ".") and not re.search(r"[*?\[]", source):
                named.append(source)
    return named


def image_context(task: Task) -> dict[str, str]:
    """The env's Dockerfile and manifests with no app: a COPY of the app's own file gets an empty one."""
    context = dict(task.manifest_files)
    for source in named_copy_sources(task.dockerfile):
        context.setdefault(source, "")
    context["Dockerfile"] = f"{task.dockerfile.rstrip()}\n{AGENT_IMAGE_TOOLS}\n"
    return context


def image_tag(task: Task, context: Mapping[str, str]) -> str:
    digest = hashlib.sha256(json.dumps(sorted(context.items())).encode()).hexdigest()[:12]
    return f"bench-agent-{re.sub(r'[^a-z0-9]+', '-', task.env.lower()).strip('-')}:{digest}"


def context_tar(context: Mapping[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, text in sorted(context.items()):
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def container_name(arm: str, task: Task) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{arm}-{task.scenario}-{task.env}".lower()).strip("-")
    return f"bench-{slug}-{uuid.uuid4().hex[:6]}"


def run_argv(name: str, image: str) -> list[str]:
    return ["docker", "run", "-d", "--name", name, "--entrypoint", "tail", image, "-f", "/dev/null"]


def exec_argv(container: str, script: str, workdir: str | None = None, stdin: bool = False) -> list[str]:
    return [
        "docker", "exec", *(["-i"] if stdin else []), *(["-w", workdir] if workdir else []),
        container, "bash", "-c", script,
    ]


def sourced(command: str) -> str:
    """As the fork's execute_in_container runs a command: every env file sourced first."""
    return "".join(f"[ -f {path} ] && source {path}\n" for path in SOURCES) + command


def baseline_script() -> str:
    ignored = " ".join(BUILD_DIRS_IGNORED)
    return (
        f"rm -rf .git && printf '%s\\n' {ignored} >> .gitignore && git init -q && git add -A && "
        "git -c user.name=bench -c user.email=bench@localhost commit -q --allow-empty -m 'BaxBench scaffold'"
    )


@dataclass(frozen=True)
class Context:
    arm: Arm
    results: Path
    artifacts: Path
    setup_script: Path
    assets: Path
    pins: Mapping[str, str]
    environ: Mapping[str, str]
    force: bool = False


def driver_argv(ctx: Context, container: str, task: Task, out: Path) -> list[str]:
    sources = [arg for path in SOURCES for arg in ("--source", path)]
    return [
        sys.executable, str(BENCH / "bench.py"), "driver",
        "--container", container,
        "--workdir", task.workdir,
        "--prompt-file", str(out / "prompt.txt"),
        "--out-dir", str(out),
        "--timeout", ctx.pins["TIMEOUT_SECONDS"],
        "--allowed-tools", ctx.pins["ALLOWED_TOOLS"],
        "--disallowed-tools", ctx.pins["DISALLOWED_TOOLS"],
        *sources,
        "--first-message-template", ctx.arm.first_message_template("greenfield"),
    ]


def test_argv(python: str, results: Path, arm: str, env: str, scenarios: list[str], mode: str, workers: int) -> list[str]:
    return [
        python, "src/main.py",
        "--models", arm,
        "--mode", mode,
        "--envs", env,
        "--scenarios", *scenarios,
        "--n_samples", "1",
        "--only_samples", str(SAMPLE),
        "--temperature", str(TEMPERATURE),
        "--spec_type", "openapi",
        "--safety_prompt", "none",
        "--results_dir", str(results),
        "--max_concurrent_runs", str(workers),
    ]


def by_env(tasks: list[Task]) -> dict[str, list[str]]:
    """BaxBench crosses --envs with --scenarios, so one call per env names exactly its tasks."""
    groups: dict[str, list[str]] = {}
    for task in tasks:
        groups.setdefault(task.env, []).append(task.scenario)
    return {env: sorted(scenarios) for env, scenarios in sorted(groups.items())}


def sh(argv: list[str], log: Path | None = None, stdin: bytes | str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    data = stdin.encode() if isinstance(stdin, str) else stdin
    done = subprocess.run(argv, input=data, capture_output=True, check=False)
    if log is not None:
        with log.open("ab") as handle:
            handle.write(f"$ {shlex.join(argv[:6])}{' ...' if len(argv) > 6 else ''}\n".encode())
            handle.write(done.stdout + done.stderr)
    if check and done.returncode != 0:
        raise RuntimeError(f"{shlex.join(argv[:4])} exited {done.returncode}: {done.stderr.decode(errors='replace')[-2000:]}")
    return done


_image_locks: dict[str, threading.Lock] = {}
_image_locks_guard = threading.Lock()


def ensure_image(task: Task, log: Path) -> str:
    context = image_context(task)
    tag = image_tag(task, context)
    with _image_locks_guard:
        lock = _image_locks.setdefault(tag, threading.Lock())
    with lock:
        if sh(["docker", "image", "inspect", tag], check=False).returncode != 0:
            sh(["docker", "build", "-t", tag, "-"], log=log, stdin=context_tar(context))
    return tag


def write_env_file(container: str, env: Mapping[str, str]) -> None:
    sh(exec_argv(container, f"umask 077 && cat > {AGENT_ENV_FILE}", stdin=True), stdin=runenv.env_script(env))


def run_task(ctx: Context, task: Task) -> dict:
    out = ctx.artifacts / esc(ctx.arm.label) / esc(task.scenario) / esc(task.env)
    record_path = out / "task.json"
    code = code_dir(ctx.results, ctx.arm.label, task)
    if not ctx.force and record_path.exists() and code.exists():
        return json.loads(record_path.read_text(encoding="utf-8"))
    # A run starts clean: BaxBench skips a sample that already has
    # test_results.json, and report reads whatever summary.json it finds, so
    # a previous attempt's files would stand in for this one's.
    for stale in (out, code.parent):
        shutil.rmtree(stale, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runner.log"
    log.write_text("", encoding="utf-8")
    record: dict = {"arm": ctx.arm.label, "scenario": task.scenario, "env": task.env, "started": pinfile.now()}
    container = container_name(ctx.arm.label, task)
    try:
        record["image"] = ensure_image(task, log)
        sh(run_argv(container, record["image"]), log=log)
        record["container"] = container
        sh(exec_argv(container, baseline_script(), workdir=task.workdir), log=log)
        sh(["docker", "cp", f"{ctx.assets}/.", f"{container}:{CONTAINER_ASSETS}"], log=log)
        sh(["docker", "cp", str(ctx.setup_script), f"{container}:{CONTAINER_SETUP}"], log=log)
        setup_env = {
            "CLAUDE_CODE_VERSION": ctx.pins["CLAUDE_CODE_VERSION"],
            "BENCH_ASSETS": CONTAINER_ASSETS,
            "BENCH_PROJECT_DIR": task.workdir,
        }
        write_env_file(container, setup_env)
        setup = sh(exec_argv(container, sourced(f"bash {CONTAINER_SETUP}"), workdir=task.workdir), check=False)
        (out / "setup.log").write_bytes(setup.stdout + setup.stderr)
        record["setup_ok"] = setup.returncode == 0
        if not record["setup_ok"]:
            record["error"] = f"setup exited {setup.returncode}"
            return record
        write_env_file(container, runenv.agent_env(ctx.environ))
        (out / "prompt.txt").write_text(task.prompt, encoding="utf-8")
        timeout = float(ctx.pins["TIMEOUT_SECONDS"]) + DRIVER_GRACE_SECONDS
        with (out / "driver.log").open("wb") as driver_log:
            try:
                driver = subprocess.run(driver_argv(ctx, container, task, out), stdout=driver_log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
                record["driver_exit"] = driver.returncode
            except subprocess.TimeoutExpired:
                record["driver_exit"] = None
                record["error"] = f"driver still running {timeout:.0f}s after it started"
    except Exception as error:
        record["error"] = str(error)
    finally:
        record.update(collect(container, task, out, code, log))
        sh(["docker", "rm", "-f", container], log=log, check=False)
        record["ended"] = pinfile.now()
        pinfile.write_json(record_path, record)
    return record


def collect(container: str, task: Task, out: Path, code: Path, log: Path) -> dict:
    """Stop what the agent left running, then take the app out of the container."""
    sh(["docker", "exec", container, "bash", "-c", "kill -KILL -1"], log=log, check=False)
    raw = out / "code-from-container"
    if raw.exists():
        shutil.rmtree(raw)
    taken = sh(["docker", "cp", f"{container}:{task.workdir}/code", str(raw)], log=log, check=False)
    if code.exists():
        shutil.rmtree(code)
    files = copy_code(raw, code) if taken.returncode == 0 else 0
    shutil.rmtree(raw, ignore_errors=True)
    code.mkdir(parents=True, exist_ok=True)
    return {"code_files": files}


def baxbench_modes(ctx: Context, tasks: list[Task], baxbench: Path, python: str, workers: int) -> None:
    logs = ctx.results / esc(ctx.arm.label)
    logs.mkdir(parents=True, exist_ok=True)
    for mode in ("test", "evaluate"):
        for env, scenarios in by_env(tasks).items():
            argv = test_argv(python, ctx.results, ctx.arm.label, env, scenarios, mode, workers)
            done = subprocess.run(argv, cwd=baxbench, capture_output=True, check=False)
            (logs / f"{mode}-{esc(env)}.log").write_bytes(done.stdout + done.stderr)
            if done.returncode != 0:
                print(f"baxbench: {mode} for {env} exited {done.returncode}", file=sys.stderr)


def run_arm(ctx: Context, tasks: list[Task], baxbench: Path, python: str, workers: int) -> list[dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(lambda task: run_task(ctx, task), tasks))
    baxbench_modes(ctx, tasks, baxbench, python, workers)
    return records
