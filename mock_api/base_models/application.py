from typing import Optional

from pydantic import BaseModel, Field


class ApplicationPostPayloadModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(None, max_length=256)


class ApplicationPatchPayloadModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
