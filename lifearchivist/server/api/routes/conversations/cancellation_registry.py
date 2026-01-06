from typing import ClassVar, Dict, Optional

from .....llm.agent.cancellation import CancellationReason, CancellationToken


class StreamCancellationRegistry:

    _instance: ClassVar[Optional["StreamCancellationRegistry"]] = None
    _tokens: ClassVar[Dict[str, CancellationToken]] = {}

    def __new__(cls) -> "StreamCancellationRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, conversation_id: str, token: CancellationToken) -> None:
        StreamCancellationRegistry._tokens[conversation_id] = token

    def unregister(self, conversation_id: str) -> None:
        StreamCancellationRegistry._tokens.pop(conversation_id, None)

    def cancel(
        self, conversation_id: str, reason: str = "User requested cancellation"
    ) -> bool:
        token = StreamCancellationRegistry._tokens.get(conversation_id)
        if token is None:
            return False
        token.cancel(CancellationReason.USER_REQUESTED, reason)
        return True

    def get(self, conversation_id: str) -> Optional[CancellationToken]:
        return StreamCancellationRegistry._tokens.get(conversation_id)

    def is_active(self, conversation_id: str) -> bool:
        return conversation_id in StreamCancellationRegistry._tokens


def get_cancellation_registry() -> StreamCancellationRegistry:
    return StreamCancellationRegistry()
