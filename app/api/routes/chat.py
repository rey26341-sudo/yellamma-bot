import uuid

from fastapi import APIRouter, HTTPException, Request

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    # The compiled graph + checkpointer live on app.state, set up once
    # at startup (see app/main.py's lifespan) rather than per-request.
    graph = http_request.app.state.chat_graph

    session_id = request.session_id or str(uuid.uuid4())
    thread_id = f"{request.business_id}:{session_id}"

    try:
        result = await graph.ainvoke(
            {
                "business_id": request.business_id,
                "message": request.message,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(reply=result["reply"], session_id=session_id)
