from pydantic import BaseModel


class ChatRequest(BaseModel):
    business_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
