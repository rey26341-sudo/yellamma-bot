"""
app/core/state.py

Shared conversation state for the LangGraph core. One shape, used by
every channel (website chat, voice, WhatsApp) and every business
config — channel-specific fields stay out of here; adapters translate
their own protocol into a `message` string and a `session_id` before
calling the graph, and translate `reply` back into whatever the
channel needs (TwiML, JSON, WhatsApp API payload, etc.).
"""

from typing import List, Optional, TypedDict


class HistoryTurn(TypedDict):
    role: str  # "user" | "assistant"
    text: str


class ChatState(TypedDict):
    business_id: str
    message: str
    history: List[HistoryTurn]

    # Booking flow (salon-style businesses)
    step: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    service: Optional[str]
    date: Optional[str]
    time: Optional[str]
    saved: bool

    reply: Optional[str]
