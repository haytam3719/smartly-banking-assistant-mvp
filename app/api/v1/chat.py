from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.dependencies import get_chat_service
from app.api.schemas import ChatRequest, ChatResponse
from app.application.chat_service import ChatService
from app.core.config import get_settings

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    x_request_id: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    settings = get_settings()
    if len(body.message) > settings.max_message_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Message is too long",
        )

    request_id, conversation_id, outcome = await service.chat(
        customer_id=body.customer_id,
        message=body.message,
        conversation_id=body.conversation_id,
        request_id=x_request_id,
    )
    return ChatResponse(
        request_id=request_id,
        conversation_id=conversation_id,
        answer=outcome.answer,
        route=outcome.route,
        source=outcome.source,
        citations=outcome.citations,
        debug_trace=outcome.debug_trace,
    )
