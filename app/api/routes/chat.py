from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.appointment_service import AppointmentService


router = APIRouter()

ai_service = AIService()
conversation_service = ConversationService()
appointment_service = AppointmentService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    user_id = "demo-user"

    session = conversation_service.get_session(user_id)

    # Store which business is using the chatbot
    session["business_id"] = request.business_id

    try:
        reply = ai_service.generate_reply(
            request.business_id,
            request.message,
            session
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    # Save appointment after all required details are collected
    if (
        session["name"]
        and session["phone"]
        and session["date"]
        and session["time"]
        and not session.get("saved")
    ):

        appointment_service.save_appointment(session)
        session["saved"] = True


    return ChatResponse(reply=reply)
