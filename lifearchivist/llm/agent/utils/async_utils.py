import asyncio
import random
from contextlib import asynccontextmanager
from typing import AsyncIterator


@asynccontextmanager
async def maybe_timeout(seconds: float | None) -> AsyncIterator[None]:
    if seconds is None:
        yield
    else:
        async with asyncio.timeout(seconds):
            yield


def compute_exponential_backoff(
    attempt: int,
    base_seconds: float = 0.5,
    max_seconds: float = 5.0,
    jitter_factor: float = 0.2,
) -> float:
    base = base_seconds * (2 ** (attempt - 1))
    jitter = jitter_factor * base * (2 * random.random() - 1)
    return float(min(max_seconds, max(0.0, base + jitter)))
