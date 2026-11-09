from __future__ import annotations

import subprocess
from pathlib import Path

import pins as pinfile
from arms import ARMS, SETUP

PINS = pinfile.load()


def test_config_holds_every_pin_the_commands_read() -> None:
    for key in ("CLAUDE_CODE_VERSION", "ANTHROPIC_MODEL", "AWS_REGION", "AIDLC_VERSION", "PLUGIN_COMMIT",
                "SUSVIBES_FORK_COMMIT", "BAXBENCH_REF", "TIMEOUT_SECONDS", "WORKERS", "ALLOWED_TOOLS", "DISALLOWED_TOOLS"):
        assert key in PINS
    assert PINS["CLAUDE_CODE_VERSION"] == "2.1.318"
    assert "mcp__security-agent__setup" in PINS["DISALLOWED_TOOLS"].split(",")
    assert "AskUserQuestion" not in PINS["ALLOWED_TOOLS"].split(",")


def test_each_setup_script_is_one_file_that_bash_parses_and_stops_on_errors(tmp_path: Path) -> None:
    for arm in ARMS.values():
        script = arm.setup_script()
        assert script.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in script.splitlines()[:3]
        for part in arm.setup_parts:
            assert (SETUP / part).read_text(encoding="utf-8") in script
        path = tmp_path / f"{arm.label}.sh"
        path.write_text(script, encoding="utf-8")
        assert subprocess.run(["bash", "-n", str(path)], check=False).returncode == 0


def test_no_setup_part_sets_an_unattended_or_bypass_switch() -> None:
    text = "".join(path.read_text(encoding="utf-8") for path in SETUP.glob("*.sh"))
    for switch in ("AIDLC_UNATTENDED", "AIDLC_SKIP_", "AIDLC_DISABLE_", "--bypass"):
        assert switch not in text


def test_arm2_and_arm3_differ_only_in_the_plugin_setup() -> None:
    assert ARMS["arm2"].first_message == ARMS["arm3"].first_message
    assert ARMS["arm3"].setup_parts == (*ARMS["arm2"].setup_parts, "security.sh")
    assert ARMS["arm2"].setup_parts == (*ARMS["arm1"].setup_parts, "aidlc.sh")
    assert ARMS["arm1"].first_message_template("brownfield") == "{prompt}"
    assert ARMS["arm2"].first_message_template("brownfield") == "/aidlc --scope classic --project-type brownfield {prompt}"


def test_arm3_gets_the_security_agent_setup_for_its_region_only(tmp_path: Path) -> None:
    import json

    import build_assets

    source = tmp_path / "config.json"
    source.write_text(json.dumps({
        "ap-southeast-1": {"agent_space_id": "as-1", "service_role": "arn:role", "s3_bucket": "b", "code_reviews": {"/w": "cr-1"}},
        "us-east-1": {"agent_space_id": "as-2"},
    }))
    assert build_assets.security_agent_config(source, "ap-southeast-1") == {
        "ap-southeast-1": {"agent_space_id": "as-1", "service_role": "arn:role", "s3_bucket": "b"}
    }
    assert build_assets.security_agent_config(source, "eu-west-1") is None
    assert build_assets.security_agent_config(tmp_path / "missing.json", "ap-southeast-1") is None
