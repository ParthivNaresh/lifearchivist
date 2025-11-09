"""
LLM Provider management endpoints.

Provides CRUD operations for LLM providers including:
- Adding and configuring providers (OpenAI, Ollama, Anthropic, etc.)
- Listing and filtering providers
- Testing provider credentials
- Managing default provider
- Listing available models per provider
- Generating text with specific providers

Security Note:
    This API is designed for local-first, single-user desktop applications.
    No authentication is required as the API runs on localhost and is only
    accessible to the local user. The "credentials" managed here are API keys
    for external LLM providers (OpenAI, Anthropic, etc.), not authentication
    credentials for this API.

    For multi-tenant deployments, add authentication middleware and user isolation.
"""

from fastapi import APIRouter

from . import (
    add,
    delete,
    generate,
    get,
    list,
    list_models,
    metadata,
    set_default,
    test,
    update,
    usage_check,
)

router = APIRouter(prefix="/providers", tags=["providers"])

router.include_router(add.router)
router.include_router(list.router)
router.include_router(get.router)
router.include_router(usage_check.router)
router.include_router(delete.router)
router.include_router(update.router)
router.include_router(test.router)
router.include_router(list_models.router)
router.include_router(generate.router)
router.include_router(set_default.router)
router.include_router(metadata.router)

__all__ = ["router"]
