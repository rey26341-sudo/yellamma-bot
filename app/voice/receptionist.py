"""
app/voice/receptionist.py

Provider-agnostic conversation core for the clinic AI receptionist.
Adapters (app/voice/adapters/*) handle telephony-specific audio
in/out; this module owns the actual booking conversation and knows
nothing about Exotel, Twilio, or any other provider.

    Adapter (audio in) -> stt -> receptionist.handle_turn -> tts -> Adapter (audio out)

INTEGRATION NOTE
-----------------
This currently calls Gemini directly via google-genai as a
self-contained conversation engine (see `generate_reply` below). You
already have app/services/gemini_service.py, conversation_service.py,
and appointment_service.py — if those implement overlapping logic
(prompting Gemini, tracking booking state, writing appointments),
this should probably delegate to them instead of duplicating it.
Share those files and I'll wire `handle_turn` to call into your
existing services rather than re-implementing the conversation
engine here.
"""

import asyncio
import json
import os
from typing import Optional

from fastapi import APIRouter
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.voice.adapters import exotel as exotel_adapter
from app.voice.adapters import twilio as twilio_adapter
from app.voice.session import load_session, save_session

CLINIC_NAME = "our clinic"  # e.g. "Sunrise Dental Care"
GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = f"""\
You are a calm, warm, professional AI voice receptionist for {CLINIC_NAME},
a clinic offering skin care, hair care, dental care, and general
consultation services.

Your job is to collect four pieces of information from the caller, one
step at a time, in a natural conversational way: their name, the
service they want, a preferred date, and a preferred time. Once you
have all four, summarize the appointment and ask the caller to
confirm before booking it.

Rules:
- Ask only one question at a time. Keep replies short (1-2 sentences),
  soft-spoken, and reassuring — this is a clinic, some callers may be
  anxious.
- Never invent information the caller hasn't given you. If a field is
  still unknown, leave it as an empty string.
- Carry forward any slot values already collected (given to you as
  "known so far") unless the caller corrects them.
- Once you have name, service, date, and time, ask the caller to
  confirm ("Shall I go ahead and book this?") before setting step to
  "confirm".
- Only set call_should_end to true once the caller has explicitly
  confirmed (book it) or explicitly declined (cancel/don't book it —
  in that case still end the call politely without booking).
- If the caller's input is unclear or off-topic, gently steer them
  back to the current question without ending the call.
- Reply in the same language/style the caller is using where
  reasonable, but default to a warm, plain, professional tone.
"""


def greeting_text() -> str:
    return (
        f"Welcome to SUNRISE CLINIC. I'm here to help you book an "
        "appointment. May I have your name, please?"
    )


class BookingTurn(BaseModel):
    name: str
    service: str
    date: str
    time: str
    step: str          # "name" | "service" | "date" | "time" | "confirm" | "done"
    reply: str          # what the receptionist should say next
    call_should_end: bool


_genai_client: Optional[genai.Client] = None


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _genai_client


def _build_turn_prompt(session: dict, caller_said: str) -> str:
    known = {k: session.get(k, "") for k in ("name", "service", "date", "time")}
    return (
        f"Known so far: {json.dumps(known)}\n"
        f"Current step: {session.get('step', 'name')}\n"
        f"Caller just said: \"{caller_said}\"\n\n"
        "Update the booking slots and produce the next reply, following "
        "the system instructions."
    )


def _generate_turn_blocking(session: dict, caller_said: str) -> BookingTurn:
    client = _get_genai_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=_build_turn_prompt(session, caller_said),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=BookingTurn,
            temperature=0.3,
        ),
    )
    return BookingTurn.model_validate_json(response.text)


async def generate_reply(session: dict, caller_said: str) -> tuple[dict, str, bool]:
    """
    Run one transcript -> LLM turn. Returns (updated_session,
    reply_text, call_should_end). Falls back to a gentle re-prompt if
    the LLM call fails, rather than crashing the call.

    TODO: replace this function's body with a call into
    app/services/conversation_service.py + gemini_service.py once
    their interfaces are confirmed, so there's one conversation
    engine, not two.
    """
    if not caller_said.strip():
        return session, "I'm sorry, I didn't quite hear that. Could you say it again?", False

    try:
        turn = await asyncio.to_thread(_generate_turn_blocking, session, caller_said)
    except Exception:
        return session, "Sorry, could you say that again for me?", False

    session.update({
        "name": turn.name,
        "service": turn.service,
        "date": turn.date,
        "time": turn.time,
        "step": turn.step,
    })

    if turn.step == "done":
        # TODO: persist booking via app/services/appointment_service.py
        # TODO: send WhatsApp/SMS confirmation to the patient
        # TODO: notify clinic front desk / calendar
        pass

    return session, turn.reply, turn.call_should_end


async def handle_turn(session_id: str, caller_said: str) -> tuple[dict, str, bool]:
    """
    The single entry point every adapter calls: load session state,
    run one conversation turn, persist state, return what to say next
    and whether the call is over. Nothing telephony-specific here.
    """
    session = await load_session(session_id)
    session, reply_text, call_should_end = await generate_reply(session, caller_said)
    await save_session(session_id, session)
    return session, reply_text, call_should_end


# ---------------------------------------------------------------------
# Router — mounts every active telephony adapter side by side. Both
# Exotel (India) and Twilio (international) callers land on the same
# conversation core above — the adapter is the only part that knows
# which provider a given call came in on.
# ---------------------------------------------------------------------

router = APIRouter(prefix="/voice")
router.include_router(exotel_adapter.router)
router.include_router(twilio_adapter.router)
