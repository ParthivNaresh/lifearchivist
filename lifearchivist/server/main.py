"""
Main FastAPI application creation and configuration.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import get_settings
from ..config.settings import configure_logging
from .api.dependencies import set_server_instance
from .api.router import get_api_router
from .mcp_server import MCPServer


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""

    tool: str
    params: Dict[str, Any]
    session_id: str = None


class ToolExecutionResult(BaseModel):
    """Result of tool execution."""

    success: bool
    result: Dict[str, Any] = None
    error: str = None


# Global server instance
server = MCPServer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    configure_logging(level="INFO", use_structured=True)
    await server.initialize()
    set_server_instance(server)
    yield
    # Shutdown
    # No explicit cleanup needed


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_settings()

    # Adjust app configuration based on mode
    title = (
        "Life Archivist API" if settings.api_only_mode else "Life Archivist MCP Server"
    )
    description = (
        "Local-first document processing API"
        if settings.api_only_mode
        else "Local-first personal knowledge system with MCP architecture"
    )

    app = FastAPI(
        title=title,
        description=description,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware only if UI is enabled or API-only mode
    if settings.enable_ui or settings.api_only_mode:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        if settings.api_only_mode:
            origins.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "mode": "api-only" if settings.api_only_mode else "full",
            "vault": server.vault is not None,
            "llamaindex": server.llamaindex_service is not None,
            "agents_enabled": settings.enable_agents,
            "websockets_enabled": settings.enable_websockets,
            "ui_enabled": settings.enable_ui,
        }

    # Tool execution endpoint (for backwards compatibility)
    @app.post("/api/tools/execute")
    async def execute_tool(request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a tool via REST API."""
        result = await server.execute_tool(request.tool, request.params)
        return ToolExecutionResult(**result)

    # Include all API routes
    app.include_router(get_api_router())

    return app


if __name__ == "__main__":
    import uvicorn

    from ..config import get_settings

    settings = get_settings()
    uvicorn.run(
        "lifearchivist.server.main:create_app",
        host=settings.host,
        port=settings.port,
        reload=True,
        factory=True,
    )
