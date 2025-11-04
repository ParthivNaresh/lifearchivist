"""
Add provider endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .provider_utils import create_provider_config, parse_provider_type
from .request_models import AddProviderRequest
from .utils import validate_credential_service, validate_llm_manager

router = APIRouter()


@router.post("/")
async def add_provider(request: AddProviderRequest):
    """
    Add a new LLM provider.

    Validates configuration, stores encrypted credentials, and initializes the provider.

    Example:
        ```json
        {
            "provider_id": "my-openai",
            "provider_type": "openai",
            "config": {
                "api_key": "sk-...",
                "organization": "org-..."
            },
            "set_as_default": true
        }
        ```
    """
    server = get_server()
    llm_manager, error_response = validate_llm_manager(server)
    if error_response:
        return error_response

    credential_service, error_response = validate_credential_service(server)
    if error_response:
        return error_response

    assert llm_manager is not None
    assert credential_service is not None

    try:
        try:
            provider_type = parse_provider_type(request.provider_type)
            config = create_provider_config(provider_type, request.config)
        except Exception as e:
            from fastapi import HTTPException as FastAPIHTTPException

            if isinstance(e, FastAPIHTTPException) and e.status_code == 400:
                from ..shared.responses import validation_error_response

                return validation_error_response(e.detail)
            raise

        store_result = await credential_service.add_provider(
            provider_id=request.provider_id,
            provider_type=provider_type,
            config=config,
            is_default=request.set_as_default,
        )

        if store_result.is_failure():
            return JSONResponse(
                content=store_result.to_dict(),
                status_code=store_result.status_code,
            )

        if server.provider_loader:
            load_result = await server.provider_loader.load_provider(
                request.provider_id
            )

            if load_result.is_failure():
                await credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=load_result.to_dict(),
                    status_code=load_result.status_code,
                )

            provider = load_result.unwrap()

            add_result = await llm_manager.add_provider(
                provider, set_as_default=request.set_as_default
            )

            if add_result.is_failure():
                await credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=add_result.to_dict(),
                    status_code=add_result.status_code,
                )

        return success_response(
            {
                "provider_id": request.provider_id,
                "provider_type": provider_type.value,
                "is_default": request.set_as_default,
                "message": "Provider added successfully",
            }
        )

    except Exception as e:
        return internal_error_response("Add provider", e)
