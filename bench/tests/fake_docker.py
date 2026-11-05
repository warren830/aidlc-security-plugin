#!/usr/bin/env python3
"""A stand-in for `docker exec`, for driver tests: the "container" is a host directory.

The command runs with only what a container would see from the caller: a
fixed PATH and HOME (FAKE_DOCKER_PATH, FAKE_DOCKER_HOME), plus the variables
named by `-e NAME`, whose values `docker exec` takes from its own environment.
Each call is appended to FAKE_DOCKER_LOG.
"""

import json
import os
import sys


def main() -> None:
    args = sys.argv[1:]
    with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as handle:
        claude_env = {name: value for name, value in os.environ.items() if name.startswith("CLAUDE")}
        handle.write(json.dumps({"argv": args, "env_names": sorted(os.environ), "claude_env": claude_env}) + "\n")
    if args[:1] != ["exec"]:
        sys.exit(f"fake docker: only exec is supported, got {args[:1]}")
    args = args[1:]
    workdir, forwarded = None, []
    while args and args[0].startswith("-"):
        flag = args.pop(0)
        if flag == "-i":
            continue
        if flag == "-w":
            workdir = args.pop(0)
        elif flag == "-e":
            forwarded.append(args.pop(0))
        else:
            sys.exit(f"fake docker: unsupported flag {flag}")
    container, command = args[0], args[1:]
    if "=" in "".join(forwarded):
        sys.exit("fake docker: a value was passed on the command line")
    env = {"PATH": os.environ["FAKE_DOCKER_PATH"], "HOME": os.environ["FAKE_DOCKER_HOME"], "FAKE_CONTAINER": container}
    env.update({name: os.environ[name] for name in forwarded if name in os.environ})
    if workdir:
        os.chdir(workdir)
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    main()
