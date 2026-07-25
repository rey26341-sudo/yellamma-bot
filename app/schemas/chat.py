"""
Before: `business_id` came straight from the request body and was used
directly to build the LangGraph thread_id and presumably to resolve
the config profile — so any caller could claim to be any business and
read/write into that business's conversation state.

Now: the caller authenticates with a per-tenant API key (X-API-Key
header). The tenant — and therefore which config profile loads, and
what thread_id prefix is used — comes from that key server-side. The
client no longer supplies business_id at all; there's nothing left for
it to lie about.

NOTE: this assumes ChatRequest currently has a `business_id: str`
field (per the README's example payload). That field should be
*removed* from app/schemas/chat.py — leaving it in but just ignoring
it is weaker, since silently-ignored input is a common source of
regressions when someone "helpfully" wires it back up later. I haven't
seen the real schemas/chat.py, so please reconcile this against
whatever else lives on that class (I obviously won't have removed
any other fields it needs, since I never saw it).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_api_key
from app.database.database import get_db
from app.models.api_key import APIKey
from app.models.tenant import Tenant
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    api_key: APIKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == api_key.tenant_id))
    tenant = result.scalar_one_or_none()

    if tenant is None or not tenant.is_active:
        # Shouldn't happen (FK + cascade should keep these in sync) but
        # fail closed rather than falling through with an unset tenant.
        raise HTTPException(status_code=401, detail="Invalid API key")

    graph = http_request.app.state.chat_graph
    session_id = request.session_id or str(uuid.uuid4())
    # tenant.slug, not anything from the request — this is the value
    # config_loader.py and the thread_id both need, and it now comes
    # only from the authenticated key.
    thread_id = f"{tenant.slug}:{session_id}"

    try:
        result = await graph.ainvoke(
            {
                "business_id": tenant.slug,
                "tenant_id": str(tenant.id),
                "message": request.message,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(reply=result["reply"], session_id=session_id)
