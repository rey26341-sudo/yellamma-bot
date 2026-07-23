from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    business_id: str
    message: str
    # NEW: identifies one visitor's conversation. The frontend should
    # generate one (e.g. a UUID) on first load and keep sending it on
    # every subsequent message so the graph's checkpointer can find
    # the right conversation state. If omitted, a session_id is
    # generated server-side and returned — but that means each
    # request without one starts a brand-new conversation, so the
    # frontend should always send the one it got back.
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
