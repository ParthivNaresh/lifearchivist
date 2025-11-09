"""
Utility functions for provider endpoints.
"""

from typing import Any, Dict

from fastapi import HTTPException

from lifearchivist.llm import ProviderType


def parse_provider_type(provider_type_str: str) -> ProviderType:
    """Parse provider type string to enum."""
    try:
        return ProviderType(provider_type_str.lower())
    except ValueError:
        valid_types = [t.value for t in ProviderType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type '{provider_type_str}'. Valid types: {valid_types}",
        ) from None


def create_provider_config(provider_type: ProviderType, config_dict: Dict[str, Any]):
    """Create typed provider config from dict."""
    try:
        from lifearchivist.llm.provider_config import create_provider_config

        return create_provider_config(provider_type, **config_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: {str(e)}",
        ) from e
