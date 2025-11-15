from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConversationContext:
    conversation_id: str
    user_id: str
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
