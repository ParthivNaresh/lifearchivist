from typing import Optional

from pydantic import BaseModel, Field


class AddFolderRequest(BaseModel):
    """Request to add a watched folder."""

    folder_path: str = Field(
        description="Absolute path to folder to watch",
        examples=["/Users/username/Documents"],
    )
    enabled: bool = Field(
        default=True, description="Whether to start watching immediately"
    )


class UpdateFolderRequest(BaseModel):
    """Request to update a watched folder."""

    enabled: Optional[bool] = Field(
        default=None, description="Enable or disable watching"
    )
