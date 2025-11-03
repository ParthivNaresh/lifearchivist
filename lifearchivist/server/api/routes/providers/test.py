"""
Test provider endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..shared.dependencies import get_server

router = APIRouter()


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str):
    """
    Test provider credentials and connectivity.

    Validates that the provider can be reached and credentials are valid.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        is_valid = await provider.validate_credentials()

        return {
            "success": True,
            "provider_id": provider_id,
            "is_valid": is_valid,
            "message": "Credentials valid" if is_valid else "Credentials invalid",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
