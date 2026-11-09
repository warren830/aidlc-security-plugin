#!/usr/bin/env python3
"""A scripted stand-in for the Claude Code CLI in stream-json mode, for driver tests.

It speaks the side of the protocol the Agent SDK expects (claude_agent_sdk
_internal/query.py and transport/subprocess_cli.py): it answers `initialize`
and `interrupt` control requests, sends `can_use_tool` control requests and
waits for their responses, and writes assistant, user, system and result
frames. Its behaviour is `.fake-claude/scenario.json` in its working
directory: one list of steps per user message it receives. It appends what it
receives to `.fake-claude/log.jsonl`.
"""

import json
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

STATE = Path(".fake-claude")
SESSION = "fake-session"
MODEL = "fake-model"

_write_lock = threading.Lock()
_responses: dict[str, dict] = {}
_response_ready = threading.Condition()
_users: queue.Queue = queue.Queue()
_interrupted = threading.Event()


def log(event: str, **data) -> None:
    with (STATE / "log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": event, "time": time.time(), **data}) + "\n")


def emit(frame: dict) -> None:
    with _write_lock:
        sys.stdout.write(json.dumps(frame) + "\n")
        sys.stdout.flush()


def reader() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        frame = json.loads(line)
        kind = frame.get("type")
        if kind == "control_request":
            request = frame["request"]
            if request.get("subtype") == "interrupt":
                log("interrupt")
                _interrupted.set()
            emit(
                {
                    "type": "control_response",
                    "response": {"subtype": "success", "request_id": frame["request_id"], "response": {}},
                }
            )
        elif kind == "control_response":
            response = frame["response"]
            with _response_ready:
                _responses[response["request_id"]] = response
                _response_ready.notify_all()
        elif kind == "user":
            _users.put(frame)
    log("eof")
    _users.put(None)


def ask_permission(tool_name: str, tool_input: dict, tool_use_id: str) -> dict:
    request_id = f"perm-{uuid.uuid4().hex[:8]}"
    emit(
        {
            "type": "control_request",
            "request_id": request_id,
            "request": {
                "subtype": "can_use_tool",
                "tool_name": tool_name,
                "input": tool_input,
                "permission_suggestions": [],
                "tool_use_id": tool_use_id,
            },
        }
    )
    with _response_ready:
        _response_ready.wait_for(lambda: request_id in _responses)
        response = _responses.pop(request_id)
    log("permission", tool=tool_name, response=response)
    return response


def assistant(content: list) -> None:
    emit(
        {
            "type": "assistant",
            "message": {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "type": "message",
                "role": "assistant",
                "model": MODEL,
                "content": content,
                "stop_reason": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
            "parent_tool_use_id": None,
            "session_id": SESSION,
            "uuid": str(uuid.uuid4()),
        }
    )


def tool_result(tool_use_id: str, text: str) -> None:
    emit(
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": text}]},
            "parent_tool_use_id": None,
            "session_id": SESSION,
            "uuid": str(uuid.uuid4()),
        }
    )


def system(subtype: str, **fields) -> None:
    emit({"type": "system", "subtype": subtype, "session_id": SESSION, "uuid": str(uuid.uuid4()), **fields})


def session_state(state: str) -> None:
    if os.environ.get("CLAUDE_CODE_SDK_READS_SESSION_STATE") == "1":
        emit({"type": "system", "subtype": "session_state_changed", "state": state, "sdk_host_only": True})


def result(spec: dict) -> None:
    is_error = bool(spec.get("is_error"))
    frame = {
        "type": "result",
        "subtype": spec.get("subtype", "error_during_execution" if is_error else "success"),
        "duration_ms": 10,
        "duration_api_ms": 5,
        "is_error": is_error,
        "num_turns": spec.get("num_turns", 1),
        "session_id": SESSION,
        "total_cost_usd": spec.get("cost", 0.0),
        "usage": spec.get("usage", {"input_tokens": 1, "output_tokens": 1}),
        "modelUsage": spec.get("model_usage", {}),
        "permission_denials": [],
        "result": spec.get("text", ""),
        "uuid": str(uuid.uuid4()),
    }
    if "errors" in spec:
        frame["errors"] = spec["errors"]
    emit(frame)
    session_state("idle")


def interruptible_sleep(seconds: float) -> bool:
    """Sleep; True when an interrupt cut it short (the turn then ends aborted)."""
    if _interrupted.wait(seconds):
        _interrupted.clear()
        result({"is_error": True, "cost": 0.0, "text": "", "errors": ["Request was aborted."]})
        return True
    return False


def run_step(step: dict) -> bool:
    """Run one step; False ends the turn early."""
    if "say" in step:
        assistant([{"type": "text", "text": step["say"]}])
    elif "ask" in step:
        tool_use_id = f"toolu_{uuid.uuid4().hex[:8]}"
        tool_input = {"questions": step["ask"]}
        assistant([{"type": "tool_use", "id": tool_use_id, "name": "AskUserQuestion", "input": tool_input}])
        response = ask_permission("AskUserQuestion", tool_input, tool_use_id).get("response", {})
        if response.get("behavior") == "deny" and response.get("interrupt"):
            result({"is_error": True, "cost": 0.0, "errors": ["Request was aborted."]})
            return False
        tool_result(tool_use_id, f"answers: {json.dumps(response.get('updatedInput', {}).get('answers'))}")
    elif "tool" in step:
        tool_use_id = f"toolu_{uuid.uuid4().hex[:8]}"
        tool = step["tool"]
        assistant([{"type": "tool_use", "id": tool_use_id, "name": tool["name"], "input": tool.get("input", {})}])
        response = ask_permission(tool["name"], tool.get("input", {}), tool_use_id)
        tool_result(tool_use_id, json.dumps(response.get("response", {})))
    elif "task_started" in step:
        task = step["task_started"]
        system("task_started", task_id=task["task_id"], description="a subagent", task_type=task.get("task_type", "local_agent"))
    elif "task_updated" in step:
        task = step["task_updated"]
        system("task_updated", task_id=task["task_id"], patch={"status": task.get("status", "completed")})
    elif "task_notification" in step:
        task = step["task_notification"]
        system(
            "task_notification",
            task_id=task["task_id"],
            status=task.get("status", "completed"),
            output_file="/dev/null",
            summary="done",
        )
    elif "write" in step:
        path = Path(step["write"]["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(step["write"]["text"], encoding="utf-8")
    elif "result" in step:
        result(step["result"])
    elif "sleep" in step:
        return not interruptible_sleep(step["sleep"])
    elif "hang" in step:
        while True:
            time.sleep(1)
    elif "exit" in step:
        os._exit(step["exit"])
    return True


def main() -> None:
    STATE.mkdir(exist_ok=True)
    scenario = json.loads((STATE / "scenario.json").read_text(encoding="utf-8"))
    log("start", argv=sys.argv[1:], env=dict(os.environ))
    threading.Thread(target=reader, daemon=True).start()
    turns = list(scenario["turns"])
    first = True
    while True:
        frame = _users.get()
        if frame is None:
            return
        log("user", content=frame["message"]["content"])
        if first:
            system("init", model=MODEL, tools=[], cwd=os.getcwd())
            first = False
        session_state("running")
        steps = turns.pop(0) if turns else [{"say": "nothing scripted"}, {"result": {"cost": scenario.get("final_cost", 0.0)}}]
        for step in steps:
            if not run_step(step):
                break


if __name__ == "__main__":
    main()
