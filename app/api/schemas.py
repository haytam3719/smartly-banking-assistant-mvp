from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.enums import RouteMode
from app.domain.models import Citation


class ChatRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str
    answer: str
    route: RouteMode
    source: str
    citations: list[Citation]
    debug_trace: list[str] = Field(default_factory=list)
