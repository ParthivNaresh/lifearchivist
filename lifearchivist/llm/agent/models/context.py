from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..cancellation import CancellationToken


@dataclass
class ConversationContext:
    conversation_id: str
    user_id: str
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cancellation_token: Optional["CancellationToken"] = field(default=None)

    @property
    def is_cancelled(self) -> bool:
        if self.cancellation_token is None:
            return False
        return self.cancellation_token.is_cancelled

    def check_cancelled(self) -> None:
        if self.cancellation_token is not None:
            self.cancellation_token.check_cancelled()
