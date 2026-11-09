from __future__ import annotations

from claude_agent_sdk import ResultMessage

from driver.usage import Usage


def result(cost: float | None, turns: int = 1, models: dict | None = None, usage: dict | None = None) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=turns,
        session_id="s",
        total_cost_usd=cost,
        usage=usage,
        model_usage=models,
    )


def model(inp: int, out: int, cost: float) -> dict:
    return {"inputTokens": inp, "outputTokens": out, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0, "costUSD": cost}


def test_running_totals_are_read_from_the_latest_result_and_turns_are_summed() -> None:
    usage = Usage()
    usage.observe(result(0.5, turns=4, models={"m": model(100, 10, 0.5)}))
    usage.observe(result(0.9, turns=2, models={"m": model(180, 30, 0.9)}))
    assert (usage.total_cost_usd, usage.num_turns, usage.results) == (0.9, 6, 2)
    assert usage.tokens["input_tokens"] == 180
    assert usage.models["m"]["costUSD"] == 0.9


def test_a_total_that_drops_starts_a_new_segment_and_keeps_the_old_one() -> None:
    usage = Usage()
    usage.observe(result(0.5, models={"m": model(100, 10, 0.5)}))
    usage.observe(result(0.0, models={}))
    usage.observe(result(0.2, models={"m": model(40, 4, 0.2)}))
    assert usage.total_cost_usd == 0.7
    assert usage.tokens["input_tokens"] == 140


def test_models_add_up_across_models() -> None:
    usage = Usage()
    usage.observe(result(0.3, models={"a": model(10, 1, 0.1), "b": model(20, 2, 0.2)}))
    assert usage.tokens == {
        "input_tokens": 30,
        "output_tokens": 3,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }


def test_without_model_usage_the_per_turn_main_loop_usage_is_summed() -> None:
    usage = Usage()
    usage.observe(result(0.1, usage={"input_tokens": 5, "output_tokens": 1}))
    usage.observe(result(0.2, usage={"input_tokens": 7, "output_tokens": 2}))
    assert usage.tokens["input_tokens"] == 12
    assert usage.tokens["output_tokens"] == 3


def test_a_result_without_a_cost_keeps_the_running_total() -> None:
    usage = Usage()
    usage.observe(result(0.4))
    usage.observe(result(None))
    assert usage.total_cost_usd == 0.4
