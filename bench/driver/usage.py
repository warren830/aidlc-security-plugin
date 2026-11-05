"""Cost and tokens over every result frame of a session.

Claude Code 2.1.318 reports total_cost_usd and modelUsage as running totals
for the whole streaming session ("read the latest result rather than summing
across results"), while num_turns counts the model round trips of one turn and
usage covers the main loop of one turn only. So turns are summed and the
running totals are read from the latest result. A total that drops (a /clear,
or a zeroed result after a crash) starts a new segment, and the segment before
it is kept.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from claude_agent_sdk import ResultMessage

# summary.json (and per-turn usage) key -> modelUsage key
TOKEN_KEYS = {
    "input_tokens": "inputTokens",
    "output_tokens": "outputTokens",
    "cache_read_input_tokens": "cacheReadInputTokens",
    "cache_creation_input_tokens": "cacheCreationInputTokens",
}
MODEL_KEYS = (*TOKEN_KEYS.values(), "costUSD")


def _model_totals(model_usage: dict | None) -> dict[str, Counter]:
    return {
        model: Counter({key: entry.get(key) or 0 for key in MODEL_KEYS})
        for model, entry in (model_usage or {}).items()
        if isinstance(entry, dict)
    }


@dataclass
class Usage:
    results: int = 0
    num_turns: int = 0
    _cost: float = 0.0
    _banked_cost: float = 0.0
    _models: dict[str, Counter] = field(default_factory=dict)
    _banked_models: dict[str, Counter] = field(default_factory=dict)
    _main_loop: Counter = field(default_factory=Counter)

    def observe(self, result: ResultMessage) -> None:
        self.results += 1
        self.num_turns += result.num_turns or 0
        cost = result.total_cost_usd if result.total_cost_usd is not None else self._cost
        if cost < self._cost:
            self._banked_cost += self._cost
            for model, totals in self._models.items():
                self._banked_models.setdefault(model, Counter()).update(totals)
            self._models = {}
        self._cost = cost
        if result.model_usage is not None:
            self._models = _model_totals(result.model_usage)
        for key in TOKEN_KEYS:
            self._main_loop[key] += (result.usage or {}).get(key) or 0

    @property
    def total_cost_usd(self) -> float:
        return round(self._banked_cost + self._cost, 6)

    @property
    def models(self) -> dict[str, dict[str, float]]:
        merged: dict[str, Counter] = {}
        for source in (self._banked_models, self._models):
            for model, totals in source.items():
                merged.setdefault(model, Counter()).update(totals)
        return {model: {key: totals[key] for key in MODEL_KEYS} for model, totals in sorted(merged.items())}

    @property
    def tokens(self) -> dict[str, int]:
        models = self.models
        if not models:
            return {key: self._main_loop[key] for key in TOKEN_KEYS}
        return {key: int(sum(totals[model_key] for totals in models.values())) for key, model_key in TOKEN_KEYS.items()}
