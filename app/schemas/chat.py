from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    business_id: str = Field(default="salon")
    message: str = Field(
        ...,
        validation_alias=AliasChoices("message", "text", "prompt", "query"),
    )
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
