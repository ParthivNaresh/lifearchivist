"""
Storage layer for Life Archivist.
"""

from .credential_service import CredentialService
from .vault import Vault

__all__ = ["Vault", "CredentialService"]
