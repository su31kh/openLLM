from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=1)


class ChatResponse(BaseModel):
    model_used: str
    answer: str
    fallback_used: bool


class ModelCheckResponse(BaseModel):
    num_checked: int
    num_working: int
    working_models: List[str]

