"""
Message models for WebSocket communication.

These models define the structure of messages sent/received over WebSocket.
"""

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

from .constants import MESSAGE_TYPE_CORRELATION, MESSAGE_TYPE_DESCRIPTION


class ToolExecuteMessage(BaseModel):
    """Tool execution request message."""

    type: Literal["tool_execute"] = Field(..., description=MESSAGE_TYPE_DESCRIPTION)
    id: Optional[str] = Field(None, description=MESSAGE_TYPE_CORRELATION)
    tool: str = Field(..., description="Tool name to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "tool_execute",
                "id": "msg_123",
                "tool": "file.import",
                "params": {"path": "/path/to/file.pdf"},
            }
        }


class ToolResultMessage(BaseModel):
    """Tool execution result message."""

    type: Literal["tool_result"] = Field(
        default="tool_result", description=MESSAGE_TYPE_DESCRIPTION
    )
    id: Optional[str] = Field(None, description=MESSAGE_TYPE_CORRELATION)
    result: Dict[str, Any] = Field(..., description="Tool execution result")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "tool_result",
                "id": "msg_123",
                "result": {"success": True, "document_id": "doc_123"},
            }
        }


class ErrorMessage(BaseModel):
    """Error message."""

    type: Literal["error"] = Field(
        default="error", description=MESSAGE_TYPE_DESCRIPTION
    )
    id: Optional[str] = Field(None, description=MESSAGE_TYPE_CORRELATION)
    error: str = Field(..., description="Error message")
    error_type: str = Field(default="Error", description="Error type")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "error",
                "id": "msg_123",
                "error": "Tool execution failed",
                "error_type": "RuntimeError",
            }
        }


class ConversationSubscribeMessage(BaseModel):
    type: Literal["conversation_subscribe"] = Field(
        ..., description=MESSAGE_TYPE_DESCRIPTION
    )
    id: Optional[str] = Field(None, description=MESSAGE_TYPE_CORRELATION)
    conversation_id: str = Field(..., description="Conversation ID to subscribe to")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "conversation_subscribe",
                "id": "msg_456",
                "conversation_id": "conv_123",
            }
        }


class MessageStatusUpdate(BaseModel):
    type: Literal["message_status"] = Field(
        default="message_status", description=MESSAGE_TYPE_DESCRIPTION
    )
    id: Optional[str] = Field(None, description=MESSAGE_TYPE_CORRELATION)
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="Message ID")
    status: Literal["processing", "completed", "failed", "cancelled"] = Field(
        ..., description="Message status"
    )
    stage: Optional[Literal["searching", "found_sources", "generating"]] = Field(
        None, description="Processing stage (for status=processing)"
    )
    content: Optional[str] = Field(
        None, description="Message content (for completed/failed)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "message_status",
                "conversation_id": "conv_123",
                "message_id": "msg_789",
                "status": "processing",
                "stage": "generating",
                "metadata": {"sources_found": 3},
            }
        }


IncomingMessage = Union[ToolExecuteMessage, ConversationSubscribeMessage]
OutgoingMessage = Union[ToolResultMessage, ErrorMessage, MessageStatusUpdate]
