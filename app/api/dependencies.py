from fastapi import Request

from app.application.chat_service import ChatService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.container.chat_service
