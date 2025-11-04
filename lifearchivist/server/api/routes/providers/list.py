"""
List providers endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .utils import validate_llm_manager

router = APIRouter()


@router.get("/")
async def list_providers():
    """
    List all registered LLM providers.

    Returns provider metadata including type, default status, and health.
    """
    server = get_server()
    llm_manager, error_response = validate_llm_manager(server)
    if error_response:
        return error_response

    assert llm_manager is not None

    try:
        providers = llm_manager.list_providers()

        return success_response(
            {
                "providers": providers,
                "total": len(providers),
            }
        )

    except Exception as e:
        return internal_error_response("List providers", e)
