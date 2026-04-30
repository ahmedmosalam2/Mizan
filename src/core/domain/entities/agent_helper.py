from pydantic import BaseModel,Field
from typing import Optional, Dict, List, Any


class Task(BaseModel):
    id: str | None = None
    goal: str

    context: Optional[Dict[str, Any]] = None
    constraints: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Optional[str] = None