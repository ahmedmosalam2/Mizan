from pydantic import BaseModel
from typing import Optional


class BaseEntity(BaseModel):
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None