from fastapi import APIRouter, Depends, HTTPException
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatResponse
from app.api.deps import get_core # Legacy AI Core dependency

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    core = Depends(get_core) 
):
    """
    Chat with the AI Analytics Assistant.
    """
    try:
        service = ChatService(core)
        response = await service.process_message(
            request.message,
            request.session_id,
            request.debug
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
