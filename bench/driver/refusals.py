"""How often the model's safety systems stopped a run, read from raw.jsonl.

The SDK's ResultMessage drops the CLI's `safety_stops`, so the count comes
from the CLI's own stream. Claude Code 2.1.318 reports `safety_stops` on each
result as a running total that restarts at 0 on a resume or a /clear ("never
sum across results"), so a drop starts a new segment, as cost does in
usage.py. The system frames name each refusal: `model_refusal_no_fallback`
when the refused call is not retried, `model_refusal_fallback` when another
model answered it (config.env sets CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK, so a
non-zero count means the pin did not hold), and `model_fallback` when the
primary model failed and another one took the turn.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

SYSTEM_EVENTS = ("model_refusal_no_fallback", "model_refusal_fallback", "model_fallback")


def scan(lines: Iterable[str]) -> dict:
    events: Counter[str] = Counter(dict.fromkeys(SYSTEM_EVENTS, 0))
    refusal_stops = 0
    banked = current = 0
    last_main_stop: str | None = None
    for line in lines:
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        if not isinstance(frame, dict):
            continue
        kind = frame.get("type")
        if kind == "system" and frame.get("subtype") in SYSTEM_EVENTS:
            events[frame["subtype"]] += 1
        elif kind == "assistant":
            stop = (frame.get("message") or {}).get("stop_reason")
            if stop == "refusal":
                refusal_stops += 1
            if frame.get("parent_tool_use_id") is None and stop is not None:
                last_main_stop = stop
        elif kind == "result":
            if frame.get("stop_reason") is not None:
                last_main_stop = frame["stop_reason"]
            stops = frame.get("safety_stops")
            if isinstance(stops, int):
                if stops < current:
                    banked += current
                current = stops
    safety_stops = banked + current
    return {
        "safety_stops": safety_stops,
        "refusal_stop_reasons": refusal_stops,
        "events": dict(events),
        "stopped_by_model": bool(safety_stops or refusal_stops or events["model_refusal_no_fallback"]),
        "ended_on_refusal": last_main_stop == "refusal",
    }


def scan_file(path: Path) -> dict:
    if not path.exists():
        return scan(())
    with path.open(encoding="utf-8", errors="replace") as handle:
        return scan(handle)
