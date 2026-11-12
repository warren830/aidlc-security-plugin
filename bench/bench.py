#!/usr/bin/env python3
"""One command per arm, plus the setup and the report.

    python bench/bench.py setup
    python bench/bench.py baxbench --arm arm1|arm2|arm3 [--tasks pilot|all|FILE] [--workers N]
    python bench/bench.py susvibes --arm arm1|arm2|arm3 [--run 1|2|3] [--workers N]
    python bench/bench.py report
    python bench/bench.py compare RESULTS
    python bench/bench.py setup-script --arm arm1|arm2|arm3
    python bench/bench.py driver ...

Every command but compare and driver takes --work DIR (default ./bench-work)
and --config FILE (default bench/config.env).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import build_assets
import pins as pinfile
import report
import runenv
from arms import ARMS, Arm, write_setup_script
from baxbench import runner

BENCH = pinfile.BENCH
PILOT = BENCH / "baxbench" / "pilot_tasks.json"
PIPENV = "pipenv==2026.10.6"


@dataclass(frozen=True)
class Work:
    root: Path

    @property
    def susvibes(self) -> Path:
        return self.root / "src" / "susvibes"

    @property
    def baxbench(self) -> Path:
        return self.root / "src" / "baxbench"

    @property
    def susvibes_python(self) -> Path:
        return self.root / "venvs" / "susvibes" / "bin" / "python"

    @property
    def pipenv(self) -> Path:
        return self.root / "venvs" / "pipenv" / "bin" / "pipenv"

    @property
    def baxbench_python(self) -> Path:
        return self.baxbench / ".venv" / "bin" / "python"

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def baxbench_tasks(self) -> Path:
        return self.root / "baxbench-tasks.json"

    @property
    def setup_manifest(self) -> Path:
        return self.root / "setup.json"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def susvibes_eval(self) -> Path:
        return self.susvibes / "logs" / "eval"


def run(argv: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print(f"bench: {shlex.join(str(a) for a in argv)}", file=sys.stderr, flush=True)
    subprocess.run([str(a) for a in argv], cwd=cwd, env=env, check=True)


def checkout(url: str, path: Path, ref: str) -> str:
    if not path.exists():
        run(["git", "clone", "--filter=blob:none", url, path])
    run(["git", "-C", path, "fetch", "--tags", "origin"])
    commit = subprocess.run(
        ["git", "-C", str(path), "rev-parse", f"{ref}^{{commit}}"], capture_output=True, text=True, check=True
    ).stdout.strip()
    run(["git", "-C", path, "checkout", "--detach", commit])
    return commit


IMAGE_PATCH_MARK = "# bench: pinned for a build that still works"


def apt_snapshot_command(snapshot: str) -> str:
    lines = "".join(
        f"deb [check-valid-until=no] http://snapshot.debian.org/archive/{archive}/{snapshot} {suite} main\\n"
        for archive, suite in (("debian", "bullseye"), ("debian-security", "bullseye-security"), ("debian", "bullseye-updates"))
    )
    return f'rm -f /etc/apt/sources.list.d/debian.sources && printf "{lines}" > /etc/apt/sources.list'


def patch_baxbench_images(baxbench: Path, snapshot: str, goimports: str) -> dict[str, str]:
    """Make BaxBench v1.0.0's Dockerfiles build again, for the agent's image and its own test image alike.

    - apt: every base image is Debian bullseye. Past its LTS end the mirrors'
      bullseye-security index still names packages the pool no longer holds,
      so `apt-get install` fails with a 404 (sqlite3, git). Right after each
      FROM, apt is pointed at a snapshot (the date golang:1.23-bullseye names
      in its own commented sources lines), which serves a consistent index and
      pool.
    - Go: `go install golang.org/x/tools/cmd/goimports@latest` now resolves a
      release that needs Go 1.24, and the image has Go 1.23 with
      GOTOOLCHAIN=local. The newest release that builds on Go 1.23 is pinned.

    The env sources are reset first, so a second setup patches them once.
    """
    env_dir = baxbench / "src" / "env"
    subprocess.run(["git", "-C", str(baxbench), "checkout", "--", "src/env"], check=True)
    command = apt_snapshot_command(snapshot)
    in_source = command.replace("\\", "\\\\")
    for source in sorted(env_dir.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        patched = "".join(
            f"{line}{IMAGE_PATCH_MARK}\nRUN {in_source}\n" if line.startswith("FROM ") else line
            for line in text.splitlines(keepends=True)
        )
        patched = patched.replace("goimports@latest", f"goimports@{goimports}")
        if patched != text:
            source.write_text(patched, encoding="utf-8")
    return {"apt_after_every_FROM": command, "goimports": goimports}


def setup(work: Work, pins: dict[str, str]) -> dict:
    fork_ref = pins["SUSVIBES_FORK_COMMIT"] or f"origin/{pins['SUSVIBES_FORK_BRANCH']}"
    commits = {
        "bench": pinfile.git_head(pinfile.REPO),
        "susvibes_fork": checkout(pins["SUSVIBES_FORK_URL"], work.susvibes, fork_ref),
        "baxbench": checkout(pins["BAXBENCH_URL"], work.baxbench, pins["BAXBENCH_REF"]),
    }
    image_patch = patch_baxbench_images(work.baxbench, pins["DEBIAN_SNAPSHOT"], pins["GOIMPORTS_VERSION"])
    if not work.susvibes_python.exists():
        run([sys.executable, "-m", "venv", work.susvibes_python.parent.parent])
    run([work.susvibes_python, "-m", "pip", "install", "-q", "-r", work.susvibes / "requirements.txt"])
    run([work.susvibes_python, "-m", "pip", "install", "-q", "-e", work.susvibes])
    if not work.pipenv.exists():
        run([sys.executable, "-m", "venv", work.pipenv.parent.parent])
        run([work.pipenv.parent / "pip", "install", "-q", PIPENV])
    run([work.pipenv, "install", "--deploy"], cwd=work.baxbench, env={**os.environ, "PIPENV_VENV_IN_PROJECT": "1", "PIPENV_YES": "1"})
    assets = build_assets.build(work.assets, work.root / "asset-cache", pins)
    run([work.baxbench_python, BENCH / "baxbench" / "export_tasks.py", "--baxbench", work.baxbench, "--out", work.baxbench_tasks])
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    if pilot["baxbench_commit"] != commits["baxbench"]:
        raise SystemExit(f"pilot_tasks.json was sampled from BaxBench {pilot['baxbench_commit']}, not {commits['baxbench']}")
    manifest = {
        "finished": pinfile.now(),
        "host": pinfile.host(),
        "pins": pins,
        "commits": commits,
        "baxbench_patch": image_patch,
        "assets": assets,
    }
    pinfile.write_json(work.setup_manifest, manifest)
    return manifest


def ready(work: Work) -> dict:
    if not work.setup_manifest.exists():
        raise SystemExit(f"{work.setup_manifest} is missing: run `bench.py setup --work {work.root}` first")
    return pinfile.read_json(work.setup_manifest)


def preflight(arm: Arm, work: Work) -> None:
    """Stop before any container starts when arm 3 would stop in each one."""
    if "security.sh" in arm.setup_parts and not (work.assets / build_assets.AGENT_CONFIG).exists():
        raise SystemExit(
            f"{work.assets / build_assets.AGENT_CONFIG} is missing: do the one-time Security Agent setup "
            "(bench/README.md, Before you start), then run `bench.py setup` again"
        )


def run_manifest(path: Path, setup_manifest: dict, pins: dict[str, str], **details: object) -> dict:
    manifest = {
        "started": pinfile.now(),
        "host": pinfile.host(),
        "pins": pins,
        "commits": {**setup_manifest["commits"], "bench": pinfile.git_head(pinfile.REPO)},
        "bench_dirty": pinfile.git_dirty(pinfile.REPO),
        "assets": setup_manifest["assets"],
        **details,
    }
    pinfile.write_json(path, manifest)
    return manifest


def finish_manifest(path: Path, manifest: dict) -> None:
    pinfile.write_json(path, {**manifest, "ended": pinfile.now()})


def baxbench(work: Work, pins: dict[str, str], arm: Arm, tasks_choice: str, workers: int, force: bool) -> None:
    setup_manifest = ready(work)
    preflight(arm, work)
    if tasks_choice == "pilot":
        wanted = json.loads(PILOT.read_text(encoding="utf-8"))["tasks"]
    elif tasks_choice == "all":
        wanted = [{"scenario": t["scenario"], "env": t["env"]} for t in json.loads(work.baxbench_tasks.read_text(encoding="utf-8"))["tasks"]]
    else:
        wanted = json.loads(Path(tasks_choice).read_text(encoding="utf-8"))["tasks"]
    tasks = runner.load_tasks(work.baxbench_tasks, wanted)
    root = work.runs / "baxbench"
    arm_results = root / "results" / arm.label
    setup_script = write_setup_script(arm, arm_results / f"setup-{arm.label}.sh")
    manifest_path = arm_results / "manifest.json"
    manifest = run_manifest(
        manifest_path, setup_manifest, pins, benchmark="baxbench", arm=arm.label, workers=workers,
        tasks=[task.name for task in tasks], first_message_template=arm.first_message_template("greenfield"),
    )
    ctx = runner.Context(
        arm=arm,
        results=root / "results",
        artifacts=root / "artifacts",
        setup_script=setup_script,
        assets=work.assets,
        pins=pins,
        environ=runenv.runner_environ(pins, os.environ),
        force=force,
    )
    records = runner.run_arm(ctx, tasks, work.baxbench, str(work.baxbench_python), workers)
    finish_manifest(manifest_path, {**manifest, "agent_errors": [r for r in records if r.get("error")]})


def driver_wrapper(path: Path, template: str) -> Path:
    """The executable the SusVibes runner calls as --agent_driver, with this arm's first message."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(BENCH / 'bench.py'))} driver "
        f'--first-message-template {shlex.quote(template)} "$@"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def susvibes_argv(work: Work, pins: dict[str, str], label: str, run_dir: Path, setup_script: Path, wrapper: Path, workers: int) -> list[str]:
    return [
        str(work.susvibes_python), "parallel_batch_run.py",
        "--jsonl_file", str(work.susvibes / "datasets" / "default" / "susvibes_dataset.jsonl"),
        "--results_dir", str(run_dir / "results"),
        "--model", label,
        "--setup_script", str(setup_script),
        "--setup_assets", str(work.assets),
        "--claude_code_version", pins["CLAUDE_CODE_VERSION"],
        "--timeout", pins["TIMEOUT_SECONDS"],
        "--agent_driver", str(wrapper),
        "--allowed_tools", pins["ALLOWED_TOOLS"],
        "--disallowed_tools", pins["DISALLOWED_TOOLS"],
        "--strategy", "none",
        "--num_processes", str(workers),
        "--python_executable", str(work.susvibes_python),
    ]


def predictions(run_dir: Path) -> list[dict]:
    """The fork's records, the latest per instance when a run was started again."""
    latest = {
        record["instance_id"]: {key: record.get(key, "") for key in ("instance_id", "model_name_or_path", "model_patch")}
        for record in report.susvibes_records(run_dir)
    }
    return list(latest.values())


def susvibes(work: Work, pins: dict[str, str], arm: Arm, run_number: int, workers: int) -> None:
    setup_manifest = ready(work)
    preflight(arm, work)
    label = f"{arm.label}-run{run_number}"
    run_dir = work.runs / "susvibes" / label
    run_dir.mkdir(parents=True, exist_ok=True)
    setup_script = write_setup_script(arm, run_dir / f"setup-{arm.label}.sh")
    template = arm.first_message_template("brownfield")
    wrapper = driver_wrapper(run_dir / "agent-driver", template)
    manifest_path = run_dir / "manifest.json"
    manifest = run_manifest(
        manifest_path, setup_manifest, pins, benchmark="susvibes", arm=arm.label, run=run_number,
        workers=workers, first_message_template=template,
    )
    env = runenv.runner_environ(pins, os.environ)
    argv = susvibes_argv(work, pins, label, run_dir, setup_script, wrapper, workers)
    print(f"bench: {shlex.join(argv)}", file=sys.stderr, flush=True)
    # The runner exits 1 when one of its processes failed; what the others
    # finished is still evaluated.
    inference = subprocess.run(argv, cwd=work.susvibes / "evaluation_harness" / "claude_code", env=env, check=False)
    predicted = predictions(run_dir)
    predictions_path = run_dir / "predictions.json"
    pinfile.write_json(predictions_path, predicted)
    if predicted:
        run(
            [work.susvibes_python, "-m", "susvibes.eval.core", "--run_id", label, "--predictions_path", predictions_path,
             "--max_workers", str(workers), "--strategy", "none"],
            cwd=work.susvibes, env=env,
        )
    finish_manifest(manifest_path, {**manifest, "runner_exit": inference.returncode, "predictions": len(predicted)})


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bench.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    commands = {
        "setup": "clone and set up both benchmarks, build the assets",
        "baxbench": "run one arm on BaxBench tasks, then test and evaluate them",
        "susvibes": "run one arm on SusVibes v1.0, then evaluate it",
        "report": "write the report from every run in the work dir",
        "setup-script": "print an arm's container setup script",
    }
    for name, help_text in commands.items():
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--work", type=Path, default=Path("bench-work"))
        command.add_argument("--config", type=Path, default=pinfile.CONFIG)
        if name in ("baxbench", "susvibes", "setup-script"):
            command.add_argument("--arm", choices=sorted(ARMS), required=True)
        if name in ("baxbench", "susvibes", "report"):
            command.add_argument("--workers", type=int)
    sub.choices["baxbench"].add_argument("--tasks", default="pilot", help="pilot, all, or a JSON file with a tasks list")
    sub.choices["baxbench"].add_argument("--force", action="store_true", help="run tasks again that already finished")
    sub.choices["susvibes"].add_argument("--run", type=int, choices=(1, 2, 3), default=1)
    compare = sub.add_parser("compare", help="write comparison.md, the plugin off and on, from a folder's rows.csv")
    compare.add_argument("results", type=Path, help="a folder with the rows.csv that report wrote")
    return p


def main(argv: list[str]) -> int:
    if argv[:1] == ["driver"]:
        from driver.cli import main as driver_main

        return driver_main(argv[1:])
    args = parser().parse_args(argv)
    if args.command == "compare":
        print(report.write_comparison(args.results))
        return 0
    pins = pinfile.load(args.config)
    work = Work(args.work.resolve())
    workers = getattr(args, "workers", None) or int(pins["WORKERS"])
    if args.command == "setup":
        setup(work, pins)
    elif args.command == "baxbench":
        baxbench(work, pins, ARMS[args.arm], args.tasks, workers, args.force)
    elif args.command == "susvibes":
        susvibes(work, pins, ARMS[args.arm], args.run, workers)
    elif args.command == "report":
        files = report.write(work.root, work.root / "report", work.susvibes_eval, workers)
        print("\n".join(f"{name}: {path}" for name, path in files.items()))
    elif args.command == "setup-script":
        sys.stdout.write(ARMS[args.arm].setup_script())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
