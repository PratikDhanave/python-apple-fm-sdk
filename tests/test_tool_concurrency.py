# For licensing see accompanying LICENSE file.
# Copyright (C) 2026 Apple Inc. All Rights Reserved.

"""Regression tests for parallel tool callback completion and tool lifetime (#21)."""

import asyncio
import gc
import threading
import weakref

import apple_fm_sdk as fm
from apple_fm_sdk import _ctypes_bindings as lib
from apple_fm_sdk.generation_property import Property
from apple_fm_sdk.generation_schema import GenerationSchema


class _BudgetedWriteTool(fm.Tool):
    name = "write"
    description = "Create a new text file with the given content."

    def __init__(self, fail_after: int = 2):
        self.fail_after = fail_after
        self._lock = threading.Lock()
        self.call_count = 0
        super().__init__()

    @property
    def arguments_schema(self) -> GenerationSchema:
        return GenerationSchema(
            type_class=type("WriteArguments", (), {}),
            description="File to create",
            properties=[
                Property(name="path", type_class=str, description="File path"),
                Property(name="content", type_class=str, description="File content"),
            ],
        )

    async def call(self, args: fm.GeneratedContent) -> str:
        with self._lock:
            self.call_count += 1
            current = self.call_count
        if current > self.fail_after:
            raise RuntimeError("tool-call budget exhausted")
        path = args.value(for_property="path")
        return f"created:{path}"


class _CancellingTool(fm.Tool):
    name = "cancel_tool"
    description = "Raises CancelledError inside call()."

    @property
    def arguments_schema(self) -> GenerationSchema:
        return GenerationSchema(
            type_class=type("CancelArguments", (), {}),
            description="No-op arguments",
            properties=[
                Property(name="item", type_class=str, description="Item"),
            ],
        )

    async def call(self, args: fm.GeneratedContent) -> str:
        raise asyncio.CancelledError("inner cancellation")


def test_parallel_native_callbacks_complete_for_success_and_error(monkeypatch):
    """Concurrent callbacks from native worker threads finish every call without dropping any."""
    finished: dict[int, bytes] = {}
    finished_lock = threading.Lock()
    all_done = threading.Event()
    total_calls = 25

    def fake_finish_call(tool_ptr, call_id, output):
        with finished_lock:
            finished[int(call_id)] = bytes(output)
            if len(finished) == total_calls:
                all_done.set()

    monkeypatch.setattr(lib, "FMBridgedToolFinishCall", fake_finish_call)

    tool = _BudgetedWriteTool(fail_after=10)

    def invoke_from_native_thread(call_id: int):
        content = fm.GeneratedContent(
            {"path": f"file_{call_id}.txt", "content": str(call_id)}
        )
        # Transfer +1 retained reference just like BridgedTool.call(arguments:) does
        lib.FMRetain(content._ptr)
        tool._c_callback(content._ptr, call_id)

    threads = [
        threading.Thread(target=invoke_from_native_thread, args=(i,))
        for i in range(1, total_calls + 1)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert all_done.wait(timeout=5.0), (
        f"Expected all {total_calls} tool calls to finish, only got {len(finished)}"
    )
    assert len(finished) == total_calls
    successes = [v for v in finished.values() if v.startswith(b"created:")]
    errors = [v for v in finished.values() if b"tool-call budget exhausted" in v]
    assert len(successes) == 10
    assert len(errors) == 15


def test_cancelled_error_in_tool_still_finishes_native_call(monkeypatch):
    """CancelledError (a BaseException) in Tool.call() still invokes FMBridgedToolFinishCall."""
    done = threading.Event()
    recorded: list[bytes] = []

    def fake_finish_call(tool_ptr, call_id, output):
        recorded.append(bytes(output))
        done.set()

    monkeypatch.setattr(lib, "FMBridgedToolFinishCall", fake_finish_call)

    tool = _CancellingTool()
    content = fm.GeneratedContent({"item": "x"})
    lib.FMRetain(content._ptr)

    worker = threading.Thread(target=lambda: tool._c_callback(content._ptr, 42))
    worker.start()
    worker.join(timeout=5.0)

    assert done.wait(timeout=5.0), (
        "FMBridgedToolFinishCall was not invoked on CancelledError"
    )
    assert len(recorded) == 1
    assert b"Tool error:" in recorded[0]


def test_session_retains_inline_tool_instances_across_gc():
    """Inline tools=[Tool()] stays alive for the lifetime of LanguageModelSession."""
    session = fm.LanguageModelSession(
        instructions="Use tools when helpful.",
        tools=[_BudgetedWriteTool()],
    )
    tool_ref = weakref.ref(session._tools[0])

    gc.collect()
    gc.collect()

    assert tool_ref() is not None, (
        "Inline Tool instance was collected while session is alive"
    )

    del session
    gc.collect()
    gc.collect()
