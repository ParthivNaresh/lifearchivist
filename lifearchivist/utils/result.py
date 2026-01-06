from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
R = TypeVar("R")


@dataclass(frozen=True)
class FailurePayload:
    """
    A normalized error structure that's API/HTTP friendly.
    """

    message: str
    error_type: str = "InternalError"
    status_code: int = 500
    recoverable: bool = False
    details: Optional[Mapping[str, Any]] = None

    def to_public_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "success": False,
            "error": self.message,
            "error_type": self.error_type,
            "status_code": self.status_code,
            "recoverable": self.recoverable,
        }
        if self.details:
            d["details"] = dict(self.details)
        return d


class Result(Generic[T, E]):
    """
    Discriminated union for explicit error handling.

    Use:
        if result.is_success():
            # narrowed to Success[T, E]
            value = result.value
        else:
            # narrowed to Failure[T, E]
            log(result.error)
    """

    # ---- Narrowing checks (critical for mypy) ----
    def is_success(self) -> bool:
        return isinstance(self, Success)

    def is_failure(self) -> bool:
        return isinstance(self, Failure)

    # ---- Mapping ----
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        if isinstance(self, Success):
            return Success(f(self.value))
        return cast(Result[U, E], self)

    def map_error(self, f: Callable[[E], U]) -> Result[T, U]:
        if isinstance(self, Failure):
            return Failure(
                f(self.error),
                error_type=self.error_type,
                status_code=self.status_code,
                recoverable=self.recoverable,
                details=self.details,
            )
        return cast(Result[T, U], self)

    # ---- Flat-map / and_then ----
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        if isinstance(self, Success):
            return f(self.value)
        return cast(Result[U, E], self)

    # ---- Folding ----
    def fold(self, on_success: Callable[[T], R], on_failure: Callable[[E], R]) -> R:
        if isinstance(self, Success):
            return on_success(self.value)
        return on_failure(cast(Failure[T, E], self).error)

    # ---- Unwraps ----
    def unwrap(self) -> T:
        if isinstance(self, Success):
            success: Success[T, E] = self
            return success.value
        raise RuntimeError(
            f"unwrap() called on Failure: {cast(Failure[T, E], self).error}"
        )

    def unwrap_error(self) -> E:
        if isinstance(self, Failure):
            failure: Failure[T, E] = self
            return failure.error
        raise RuntimeError("unwrap_error() called on Success")

    # ---- Defaults / coercions ----
    def get_or_else(self, default: T) -> T:
        if isinstance(self, Success):
            success: Success[T, E] = self
            return success.value
        return default

    # ---- Introspection helpers ----
    def to_dict(self) -> Dict[str, Any]:
        if isinstance(self, Success):
            return {"success": True, "value": self.value}
        failure = cast(Failure[T, E], self)
        e = failure.error
        if isinstance(e, FailurePayload):
            return e.to_public_dict()
        out: Dict[str, Any] = {"success": False, "error": e}
        for k in ("error_type", "status_code", "recoverable", "details"):
            v = getattr(failure, k, None)
            if v is not None:
                out[k] = v
        return out

    # ---- Exception bridge ----
    def raise_if_failure(
        self, exc_factory: Optional[Callable[[E], Exception]] = None
    ) -> None:
        if isinstance(self, Failure):
            e = self.error
            if exc_factory is None:
                if isinstance(e, FailurePayload):
                    raise RuntimeError(f"{e.error_type}: {e.message}")
                raise RuntimeError(str(e))
            raise exc_factory(e)

    # Convenience property so `bool(Result)` means “success”
    def __bool__(self) -> bool:
        return self.is_success()


# -----------------------------
# Success / Failure branches
# -----------------------------
@dataclass(frozen=True)
class Success(Result[T, E]):
    value: T
    metadata: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class Failure(Result[T, E]):
    """
    Failure can carry either:
      - a structured FailurePayload in `.error` (recommended), or
      - a plain error type E (e.g., str).

    Optional metadata fields are kept to preserve your current usage.
    """

    error: E
    error_type: Optional[str] = None
    status_code: Optional[int] = None
    recoverable: Optional[bool] = None
    details: Optional[Mapping[str, Any]] = None


# -----------------------------
# Constructors / helpers
# -----------------------------
def ok(value: T) -> Success[T, Any]:
    return Success(value)


def fail(
    message_or_payload: Union[str, FailurePayload, E],
    *,
    error_type: Optional[str] = None,
    status_code: Optional[int] = None,
    recoverable: Optional[bool] = None,
    details: Optional[Mapping[str, Any]] = None,
) -> Failure[Any, Any]:
    """
    Flexible failure constructor.

    Examples:
        fail("Not found", error_type="NotFoundError", status_code=404)
        fail(FailurePayload("Not found", "NotFoundError", 404))
    """
    if isinstance(message_or_payload, FailurePayload):
        return Failure(
            message_or_payload,  # E is FailurePayload
            error_type=message_or_payload.error_type,
            status_code=message_or_payload.status_code,
            recoverable=message_or_payload.recoverable,
            details=message_or_payload.details,
        )
    return Failure(message_or_payload, error_type, status_code, recoverable, details)


def from_exception(
    exc: BaseException,
    *,
    error_type: str = "InternalError",
    status_code: int = 500,
    recoverable: bool = False,
    details: Optional[Mapping[str, Any]] = None,
) -> Failure[Any, FailurePayload]:
    payload = FailurePayload(
        message=str(exc),
        error_type=error_type,
        status_code=status_code,
        recoverable=recoverable,
        details=details,
    )
    return Failure(
        payload,
        error_type=payload.error_type,
        status_code=payload.status_code,
        recoverable=payload.recoverable,
        details=payload.details,
    )


# -----------------------------
# Batch helpers
# -----------------------------
def combine_all(results: Iterable[Result[T, E]]) -> Result[List[T], E]:
    """
    Turn an iterable of Result[T, E] into Result[List[T], E]
    (fail fast on the first Failure).
    """
    values: List[T] = []
    for r in results:
        if isinstance(r, Success):
            values.append(r.value)
        else:
            return cast(Result[List[T], E], r)
    return Success(values)


def partition(results: Iterable[Result[T, E]]) -> Tuple[List[T], List[Failure[T, E]]]:
    """Split into (all success values, all failures)."""
    ok_values: List[T] = []
    errors: List[Failure[T, E]] = []
    for r in results:
        if isinstance(r, Success):
            ok_values.append(r.value)
        else:
            errors.append(cast(Failure[T, E], r))
    return ok_values, errors
