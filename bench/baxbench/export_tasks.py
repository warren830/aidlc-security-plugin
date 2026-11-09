"""Write BaxBench's task definitions as JSON, read with BaxBench's own code.

    <BaxBench venv python> bench/baxbench/export_tasks.py --baxbench <checkout> --out tasks.json

Run it with the interpreter of BaxBench's pipenv environment: it imports
BaxBench's src/ modules. For each scenario and env it records the agent
prompt BaxBench builds (`build_prompt(env, "openapi", "none", agent=True)`)
and the Dockerfile its test phase builds, with the same RUN lines
(COMMON_DOCKER_RUN_COMMANDS and the scenario's needed packages).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SPEC_TYPE = "openapi"
SAFETY_PROMPT = "none"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baxbench", type=Path, required=True, help="BaxBench checkout")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(args.baxbench / "src"))

    import docker

    # env/base.py connects to the docker daemon at import time; reading the
    # definitions needs no daemon.
    docker.from_env = lambda *_args, **_kwargs: None
    from env import all_envs
    from env.base import COMMON_DOCKER_RUN_COMMANDS
    from scenarios import all_scenarios

    tasks = []
    for scenario in sorted(all_scenarios, key=lambda s: s.id):
        for env in sorted(all_envs, key=lambda e: e.id):
            commands = (
                COMMON_DOCKER_RUN_COMMANDS
                + scenario.needed_packages.get("_all_", [])
                + scenario.needed_packages.get(env.language, [])
            )
            tasks.append(
                {
                    "scenario": scenario.id,
                    "env": env.id,
                    "prompt": scenario.build_prompt(env, spec_type=SPEC_TYPE, safety_prompt=SAFETY_PROMPT, agent=True),
                    "dockerfile": env.build_only_docker_image_file(commands),
                    "workdir": env.workdir,
                    "manifest_files": env.manifest_files,
                    "code_filename": env.code_filename,
                }
            )

    def git(*command: str) -> str:
        done = subprocess.run(["git", "-C", str(args.baxbench), *command], capture_output=True, text=True, check=False)
        return done.stdout.strip()

    commit = git("rev-parse", "HEAD")
    export = {
        "baxbench_ref": git("describe", "--tags", "--exact-match") or commit,
        "baxbench_commit": commit,
        "spec_type": SPEC_TYPE,
        "safety_prompt": SAFETY_PROMPT,
        "scenarios": sorted(s.id for s in all_scenarios),
        "envs": sorted(e.id for e in all_envs),
        "tasks": tasks,
    }
    args.out.write_text(json.dumps(export, indent=1) + "\n", encoding="utf-8")
    print(f"exported {len(tasks)} tasks from BaxBench {commit[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
