"""The BaxBench pilot: a fixed, stratified sample of 40 (scenario, env) tasks.

    python bench/baxbench/sampler.py --tasks <export from export_tasks.py> --out bench/baxbench/pilot_tasks.json

Every scenario gets one task and SECOND_TASKS of them a second one, at most 2
per scenario; envs are dealt in a cycle, so each gets 2 or 3 tasks and a
scenario's two tasks never share an env. Scenario and env orders come from
one seeded shuffle, so the sample is the same on every machine.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SEED = 20261105
SIZE = 40
PER_SCENARIO = 2


def sample(scenarios: list[str], envs: list[str], size: int = SIZE, seed: int = SEED) -> list[dict[str, str]]:
    rng = random.Random(seed)
    scenarios, envs = sorted(scenarios), sorted(envs)
    rng.shuffle(scenarios)
    rng.shuffle(envs)
    second = size - len(scenarios)
    if not 0 <= second <= len(scenarios) * (PER_SCENARIO - 1) or len(envs) < PER_SCENARIO:
        raise ValueError(f"cannot take {size} tasks from {len(scenarios)} scenarios and {len(envs)} envs")
    slots = [scenario for index, scenario in enumerate(scenarios) for _ in range(2 if index < second else 1)]
    dealt = [envs[index % len(envs)] for index in range(size)]
    return sorted(({"scenario": s, "env": e} for s, e in zip(slots, dealt, strict=True)), key=lambda t: (t["scenario"], t["env"]))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tasks", type=Path, required=True, help="JSON written by export_tasks.py")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    export = json.loads(args.tasks.read_text(encoding="utf-8"))
    pilot = {
        "seed": SEED,
        "baxbench_ref": export["baxbench_ref"],
        "baxbench_commit": export["baxbench_commit"],
        "spec_type": export["spec_type"],
        "safety_prompt": export["safety_prompt"],
        "scenarios": export["scenarios"],
        "envs": export["envs"],
        "tasks": sample(export["scenarios"], export["envs"]),
    }
    args.out.write_text(json.dumps(pilot, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(pilot['tasks'])} tasks to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
