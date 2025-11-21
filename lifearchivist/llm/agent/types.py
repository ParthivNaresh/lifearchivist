import asyncio
from typing import Tuple, Type

from pydantic import BaseModel

ParamsModel = Type[BaseModel]

DEFAULT_RETRIABLE: Tuple[type[BaseException], ...] = (
    asyncio.TimeoutError,
    ConnectionError,
)
