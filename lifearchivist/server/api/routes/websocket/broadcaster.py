import logging
from collections import defaultdict
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from .message_models import MessageStatusUpdate

logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    def __init__(self) -> None:
        self._conversation_subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._websocket_to_conversations: Dict[WebSocket, Set[str]] = defaultdict(set)

    def subscribe(self, conversation_id: str, websocket: WebSocket) -> None:
        self._conversation_subscriptions[conversation_id].add(websocket)
        self._websocket_to_conversations[websocket].add(conversation_id)
        logger.info(
            f"WebSocket subscribed to conversation {conversation_id}. "
            f"Total subscribers: {len(self._conversation_subscriptions[conversation_id])}"
        )

    def unsubscribe(self, conversation_id: str, websocket: WebSocket) -> None:
        self._conversation_subscriptions[conversation_id].discard(websocket)
        self._websocket_to_conversations[websocket].discard(conversation_id)

        if not self._conversation_subscriptions[conversation_id]:
            del self._conversation_subscriptions[conversation_id]

        if not self._websocket_to_conversations[websocket]:
            del self._websocket_to_conversations[websocket]

        logger.info(f"WebSocket unsubscribed from conversation {conversation_id}")

    def unsubscribe_all(self, websocket: WebSocket) -> None:
        conversation_ids = list(self._websocket_to_conversations.get(websocket, set()))
        for conversation_id in conversation_ids:
            self.unsubscribe(conversation_id, websocket)

    async def broadcast_message_status(
        self,
        conversation_id: str,
        message_id: str,
        status: str,
        stage: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        subscribers = self._conversation_subscriptions.get(conversation_id, set())

        if not subscribers:
            logger.debug(
                f"No subscribers for conversation {conversation_id}, skipping broadcast"
            )
            return

        message = MessageStatusUpdate(
            conversation_id=conversation_id,
            message_id=message_id,
            status=status,  # type: ignore
            stage=stage,  # type: ignore
            content=content,
            metadata=metadata,
        )

        message_dict = message.model_dump(exclude_none=True)
        dead_connections: Set[WebSocket] = set()

        for websocket in subscribers:
            try:
                await websocket.send_json(message_dict)
            except Exception as e:
                logger.warning(
                    f"Failed to send message status to WebSocket: {e}. "
                    f"Marking connection as dead."
                )
                dead_connections.add(websocket)

        for websocket in dead_connections:
            self.unsubscribe(conversation_id, websocket)

        stage_info = f" (stage: {stage})" if stage else ""
        logger.info(
            f"Broadcasted message status '{status}'{stage_info} for message {message_id} "
            f"in conversation {conversation_id} to {len(subscribers) - len(dead_connections)} clients"
        )

    def get_subscriber_count(self, conversation_id: str) -> int:
        return len(self._conversation_subscriptions.get(conversation_id, set()))
