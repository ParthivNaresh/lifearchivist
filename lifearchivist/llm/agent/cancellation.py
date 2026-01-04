import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional, Set

from ...utils.logx import log_event


class CancellationReason(str, Enum):
    USER_REQUESTED = "user_requested"
    TIMEOUT = "timeout"
    SYSTEM_SHUTDOWN = "system_shutdown"
    RESOURCE_LIMIT = "resource_limit"
    PARENT_CANCELLED = "parent_cancelled"


@dataclass
class CancellationToken:
    _cancelled: bool = field(default=False, repr=False)
    _reason: Optional[CancellationReason] = field(default=None, repr=False)
    _message: Optional[str] = field(default=None, repr=False)
    _cancelled_at: Optional[datetime] = field(default=None, repr=False)
    _callbacks: Set[Callable[[], None]] = field(default_factory=set, repr=False)
    _children: Set["CancellationToken"] = field(default_factory=set, repr=False)
    _parent: Optional["CancellationToken"] = field(default=None, repr=False)

    @property
    def is_cancelled(self) -> bool:
        if self._cancelled:
            return True
        if self._parent is not None:
            return self._parent.is_cancelled
        return False

    @property
    def reason(self) -> Optional[CancellationReason]:
        if self._reason is not None:
            return self._reason
        if self._parent is not None:
            return self._parent.reason
        return None

    @property
    def message(self) -> Optional[str]:
        if self._message is not None:
            return self._message
        if self._parent is not None:
            return self._parent.message
        return None

    @property
    def cancelled_at(self) -> Optional[datetime]:
        if self._cancelled_at is not None:
            return self._cancelled_at
        if self._parent is not None:
            return self._parent.cancelled_at
        return None

    def cancel(
        self,
        reason: CancellationReason = CancellationReason.USER_REQUESTED,
        message: Optional[str] = None,
    ) -> None:
        if self._cancelled:
            return

        self._cancelled = True
        self._reason = reason
        self._message = message or reason.value
        self._cancelled_at = datetime.now(timezone.utc)

        log_event(
            "cancellation_token_cancelled",
            {
                "reason": reason.value,
                "message": self._message,
            },
        )

        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                log_event(
                    "cancellation_callback_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )

        for child in self._children:
            child.cancel(CancellationReason.PARENT_CANCELLED, f"Parent cancelled: {self._message}")

    def create_child(self) -> "CancellationToken":
        child = CancellationToken(_parent=self)
        self._children.add(child)
        return child

    def register_callback(self, callback: Callable[[], None]) -> None:
        if self.is_cancelled:
            try:
                callback()
            except Exception:
                pass
        else:
            self._callbacks.add(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.discard(callback)

    def check_cancelled(self) -> None:
        if self.is_cancelled:
            raise asyncio.CancelledError(self.message or "Operation cancelled")

    async def wait_for_cancellation(self) -> None:
        while not self.is_cancelled:
            await asyncio.sleep(0.1)

    def to_dict(self) -> dict:
        return {
            "is_cancelled": self.is_cancelled,
            "reason": self.reason.value if self.reason else None,
            "message": self.message,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


class CancellationScope:
    def __init__(self, token: Optional[CancellationToken] = None):
        self._token = token or CancellationToken()
        self._tasks: Set[asyncio.Task] = set()

    @property
    def token(self) -> CancellationToken:
        return self._token

    def register_task(self, task: asyncio.Task) -> None:
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))

    async def cancel_all_tasks(self) -> None:
        if not self._tasks:
            return

        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

    def cancel(
        self,
        reason: CancellationReason = CancellationReason.USER_REQUESTED,
        message: Optional[str] = None,
    ) -> None:
        self._token.cancel(reason, message)

    @property
    def is_cancelled(self) -> bool:
        return self._token.is_cancelled

    async def __aenter__(self) -> "CancellationScope":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.cancel_all_tasks()
        return False
