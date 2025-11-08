"""
Message models for WebSocket communication.

These models define the structure of messages sent/received over WebSocket.
"""

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field


class ToolExecuteMessage(BaseModel):
    """Tool execution request message."""

    type: Literal["tool_execute"] = Field(..., description="Message type")
    id: Optional[str] = Field(None, description="Message ID for correlation")
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


class AgentQueryMessage(BaseModel):
    """Agent query request message."""

    type: Literal["agent_query"] = Field(..., description="Message type")
    id: Optional[str] = Field(None, description="Message ID for correlation")
    agent: str = Field(..., description="Agent name")
    query: str = Field(..., description="Query text")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "agent_query",
                "id": "msg_124",
                "agent": "query_agent",
                "query": "What documents do I have about AI?",
            }
        }


class ToolResultMessage(BaseModel):
    """Tool execution result message."""

    type: Literal["tool_result"] = Field(
        default="tool_result", description="Message type"
    )
    id: Optional[str] = Field(None, description="Message ID for correlation")
    result: Dict[str, Any] = Field(..., description="Tool execution result")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "tool_result",
                "id": "msg_123",
                "result": {"success": True, "document_id": "doc_123"},
            }
        }


class AgentResultMessage(BaseModel):
    """Agent query result message."""

    type: Literal["agent_result"] = Field(
        default="agent_result", description="Message type"
    )
    id: Optional[str] = Field(None, description="Message ID for correlation")
    result: Dict[str, Any] = Field(..., description="Agent query result")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "agent_result",
                "id": "msg_124",
                "result": {"answer": "You have 5 documents about AI"},
            }
        }


class ErrorMessage(BaseModel):
    """Error message."""

    type: Literal["error"] = Field(default="error", description="Message type")
    id: Optional[str] = Field(None, description="Message ID for correlation")
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


IncomingMessage = Union[ToolExecuteMessage, AgentQueryMessage]
OutgoingMessage = Union[ToolResultMessage, AgentResultMessage, ErrorMessage]
