import uuid
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.schemas.chat import ChatRequest, ChatResponse
from app.database.database import session_scope
from app.models.tenant import Tenant

router = APIRouter()


async def resolve_tenant_id(business_id: str) -> str:
    async with session_scope() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == business_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Unknown business_id: {business_id}")
        return str(tenant.id)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    graph = http_request.app.state.chat_graph
    session_id = request.session_id or str(uuid.uuid4())
    thread_id = f"{request.business_id}:{session_id}"

    tenant_id = await resolve_tenant_id(request.business_id)

    try:
        result = await graph.ainvoke(
            {
                "business_id": request.business_id,
                "tenant_id": tenant_id,
                "message": request.message,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        detail = str(e)
        lower_detail = detail.lower()
        if (
            "401" in detail
            or "unauthenticated" in lower_detail
            or "unauthorized" in lower_detail
            or "no api key" in lower_detail
        ):
            raise HTTPException(
                status_code=503,
                detail="AI service authentication failed. Verify the Gemini API key in the environment.",
            )
        raise HTTPException(status_code=500, detail=detail)
    return ChatResponse(reply=result["reply"], session_id=session_id)
