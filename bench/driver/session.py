"""One scripted-user session: the SDK client around the turn machine and the person."""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock
from claude_agent_sdk._errors import MessageParseError

from driver.aidlc import NO_PROBE, Workflow
from driver.decide import Finish, Stall, Status, decide
from driver.person import Person
from driver.record import Record
from driver.transport import Transport, write_wrapper
from driver.turns import Phase, Turn
from driver.usage import Usage

INTERRUPT_SECONDS = 30.0
DRAIN_SECONDS = 15.0
PROBE_SECONDS = 60.0
# A tool result can carry a large file; the SDK's default 1 MB line limit
# would end the session on it.
MAX_MESSAGE_BYTES = 64 * 1024 * 1024
AGENT_TEXT_CHARS = 8000


@dataclass(frozen=True)
class Settings:
    transport: Transport
    first_message: str
    out_dir: Path
    timeout: float
    allowed_tools: list[str]
    disallowed_tools: list[str]
    stuck_after: int
    settle_seconds: float


class ProbeError(Exception):
    pass


def log(line: str) -> None:
    print(f"driver: {line}", file=sys.stderr, flush=True)


def describe(error: BaseException) -> str:
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"


async def probe(transport: Transport) -> Workflow:
    with anyio.fail_after(PROBE_SECONDS):
        done = await anyio.run_process(transport.probe(), cwd=transport.cwd, check=False)
    if done.returncode != 0:
        raise ProbeError(done.stderr.decode(errors="replace").strip() or f"exit {done.returncode}")
    return Workflow.parse(done.stdout.decode(errors="replace"))


async def pump(client: ClaudeSDKClient, inbox: ObjectSendStream) -> None:
    """Move the SDK's messages into an inbox the session can wait on with a timeout."""
    async with inbox:
        while True:
            try:
                async for message in client.receive_messages():
                    await inbox.send(message)
                return
            except MessageParseError as error:
                log(f"skipped a message the SDK could not parse: {error}")
            except Exception as error:
                await inbox.send(error)
                return


async def drain(inbox: ObjectReceiveStream, usage: Usage) -> None:
    """Read on until the interrupted turn's result, for its cost."""
    with anyio.move_on_after(DRAIN_SECONDS):
        while True:
            try:
                item = await inbox.receive()
            except anyio.EndOfStream:
                return
            if isinstance(item, ResultMessage):
                usage.observe(item)
                return


class Session:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.record = Record(settings.out_dir)
        self.usage = Usage()
        self.person = Person(self.record, settings.stuck_after)
        self.turn = Turn(settle_seconds=settings.settle_seconds)
        self.stall = Stall()
        self.workflow = NO_PROBE
        self.agent_text = ""
        self.error: str | None = None

    def options(self) -> ClaudeAgentOptions:
        transport = self.settings.transport
        return ClaudeAgentOptions(
            cli_path=write_wrapper(transport, self.settings.out_dir),
            cwd=transport.cwd,
            system_prompt={"type": "preset", "preset": "claude_code"},
            setting_sources=["user", "project", "local"],
            allowed_tools=self.settings.allowed_tools,
            disallowed_tools=self.settings.disallowed_tools,
            can_use_tool=self.person.can_use_tool,
            max_buffer_size=MAX_MESSAGE_BYTES,
        )

    async def run(self) -> dict:
        started = time.monotonic()
        deadline = started + self.settings.timeout
        finish = Finish(Status.ERROR, "driver_error")
        client: ClaudeSDKClient | None = None
        try:
            client = ClaudeSDKClient(self.options())
            finish = await self._converse(client, deadline)
        except Exception as error:
            self.error = describe(error)
        finally:
            if client is not None:
                with anyio.CancelScope(shield=True):
                    await client.disconnect()
            try:
                self.workflow = await probe(self.settings.transport)
            except (ProbeError, OSError, TimeoutError) as error:
                log(f"final state probe failed: {error}")
        summary = self.record.summary(finish, time.monotonic() - started, self.usage, self.workflow, self.error)
        self.record.write_summary(summary)
        log(f"{summary['status']} ({summary['reason']}) after {summary['wall_seconds']:.0f}s, ${summary['total_cost_usd']}")
        return summary

    async def _converse(self, client: ClaudeSDKClient, deadline: float) -> Finish:
        with anyio.move_on_after(max(0.0, deadline - time.monotonic())) as connecting:
            await client.connect()
        if connecting.cancelled_caught:
            return Finish(Status.TIMEOUT, "deadline")
        await client.query(self.settings.first_message)
        log("started")
        send, inbox = anyio.create_memory_object_stream(math.inf)
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(pump, client, send)
            async with inbox:
                finish = await self._loop(client, inbox, deadline)
                if finish.status in (Status.TIMEOUT, Status.STUCK) and self.turn.phase is not Phase.SETTLED:
                    if finish.status is Status.TIMEOUT:
                        with anyio.move_on_after(INTERRUPT_SECONDS):
                            try:
                                await client.interrupt()
                            except Exception as error:
                                log(f"interrupt failed: {error}")
                    await drain(inbox, self.usage)
            tasks.cancel_scope.cancel()
        return finish

    async def _loop(self, client: ClaudeSDKClient, inbox: ObjectReceiveStream, deadline: float) -> Finish:
        while True:
            if self.person.stop is not None:
                return self.person.stop
            if self.turn.phase is Phase.SETTLED:
                finish = await self._settled(client)
                if finish is not None:
                    return finish
                continue
            now = time.monotonic()
            if now >= deadline:
                return Finish(Status.TIMEOUT, "deadline")
            wake = min(deadline, self.turn.settle_at or deadline)
            with anyio.move_on_after(wake - now):
                try:
                    item = await inbox.receive()
                except anyio.EndOfStream:
                    self.error = "the CLI exited before the run ended"
                    return Finish(Status.ERROR, "cli_exited")
                if isinstance(item, BaseException):
                    self.error = describe(item)
                    return Finish(Status.ERROR, "cli_failed")
                self._observe(item)
                continue
            self.turn.tick(time.monotonic())

    def _observe(self, message: object) -> None:
        if isinstance(message, ResultMessage):
            self.usage.observe(message)
        if isinstance(message, AssistantMessage) and message.parent_tool_use_id is None:
            text = "".join(block.text for block in message.content if isinstance(block, TextBlock))
            if text:
                self.agent_text = (self.agent_text + "\n" + text)[-AGENT_TEXT_CHARS:]
        self.turn.observe(message, time.monotonic())

    async def _settled(self, client: ClaudeSDKClient) -> Finish | None:
        try:
            self.workflow = await probe(self.settings.transport)
        except (ProbeError, OSError, TimeoutError) as error:
            self.error = f"state probe failed: {error}"
            return Finish(Status.ERROR, "probe_failed")
        result = self.turn.result
        decision = decide(
            self.workflow,
            result_is_error=bool(result and result.is_error),
            unchanged_nudges=self.stall.unchanged(self.workflow.snapshot),
            stuck_after=self.settings.stuck_after,
        )
        if isinstance(decision, Finish):
            if decision.status is Status.ERROR and result is not None:
                self.error = "; ".join(result.errors or []) or (result.result or result.subtype)
            return decision
        self.record.prose(self.agent_text, self.workflow.awaiting_stage, decision.answer)
        self.stall.record(self.workflow.snapshot)
        log(f"prose turn: replied {decision.answer.value!r} ({decision.answer.rule})")
        await client.query(str(decision.answer.value))
        self.turn.resume()
        self.agent_text = ""
        return None
