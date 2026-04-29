"""
core/event_bus.py
Async publish/subscribe event bus.  All components communicate exclusively
through events — no direct coupling between strategies, risk, and execution.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Callable, Awaitable

from core.models import Event, EventType
from utils.logger import get_logger

log = get_logger(__name__)

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Lightweight async pub/sub bus.

    Usage:
        bus = EventBus()
        bus.subscribe(EventType.BAR, my_async_handler)
        await bus.publish(Event(type=EventType.BAR, payload={...}))
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False

    # ── Registration ──────────────────────────────────────────────────────────

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        """Register an async handler for a specific event type."""
        self._handlers[event_type].append(handler)
        log.debug(f"Subscribed {handler.__qualname__} to {event_type}")

    def unsubscribe(self, event_type: EventType, handler: Handler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, event: Event) -> None:
        """Enqueue an event for async dispatch."""
        await self._queue.put(event)

    def publish_sync(self, event: Event) -> None:
        """Thread-safe synchronous enqueue (from non-async contexts)."""
        self._queue.put_nowait(event)

    # ── Dispatch Loop ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Run the dispatch loop until stop() is called."""
        self._running = True
        log.info("EventBus started")
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                log.error(f"EventBus dispatch error: {exc}", exc_info=True)

    async def stop(self) -> None:
        self._running = False
        # Drain any remaining events
        while not self._queue.empty():
            event = self._queue.get_nowait()
            await self._dispatch(event)
        log.info("EventBus stopped")

    async def _dispatch(self, event: Event) -> None:
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            log.debug(f"No handlers for {event.type}")
            return
        results = await asyncio.gather(
            *(h(event) for h in handlers), return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                log.error(f"Handler error on {event.type}: {r}", exc_info=r)

    async def join(self) -> None:
        """Wait for all queued events to be processed."""
        await self._queue.join()
