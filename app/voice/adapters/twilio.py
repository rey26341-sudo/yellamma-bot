"""
app/voice/adapters/twilio.py

Twilio-specific adapter. This is the ONLY module that should know
about Twilio Media Streams' event shapes (camelCase `streamSid`,
MULAW @ 8kHz audio) or TwiML conventions. It translates Twilio's
audio stream into STT transcripts, hands each transcript to the
provider-agnostic conversation core
(`app.voice.receptionist.handle_turn`), and turns the reply back into
Twilio-formatted audio via TTS.

Flow
----
1. Twilio dials your number -> hits `/voice/incoming` (a normal HTTP
   webhook, configured in the Twilio Console under
   Phone Numbers -> your number -> "A call comes in").
2. `/voice/incoming` returns TwiML with <Connect><Stream> pointing
   back at this server's `/voice/twilio-stream` WebSocket.
3. Twilio opens that WebSocket and streams `connected` / `start` /
   `media` / `stop` / `mark` JSON events, audio as base64 MULAW
   (8kHz, mono) — a different codec from Exotel's PCM16.
4. Replies are synthesized as MULAW too, so no transcoding is needed
   in either direction.

Note: Twilio Media Streams doesn't deliver DTMF digits the way
Exotel's Voicebot Applet does — a "press 0 for the front desk" style
escalation would need a separate <Gather input="dtmf"> step in the
TwiML, not a `dtmf` WebSocket event. Not implemented here; add it via
TwiML if you need it.
"""

import base64
import json
from typing import Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from google.cloud import speech, texttospeech

from app.voice.stt import TurnListener
from app.voice.tts import synthesize_speech

router = APIRouter()

SAMPLE_RATE_HZ = 8000  # Twilio Media Streams' default rate


# ---------------------------------------------------------------------
# Inbound call webhook — configure this URL in the Twilio Console
# under your phone number's "A call comes in" setting.
# ---------------------------------------------------------------------

@router.post("/incoming")
async def incoming_call(request: Request):
    host = request.headers.get("host", "your-domain.example.com")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/voice/twilio-stream" />
    </Connect>
</Response>"""
    return Response(content=xml, media_type="application/xml")


async def _send_tts_reply(ws: WebSocket, stream_sid: str, text: str) -> None:
    """Synthesize `text` and stream it back to Twilio as media events."""
    audio = await synthesize_speech(
        text,
        encoding=texttospeech.AudioEncoding.MULAW,
        sample_rate_hertz=SAMPLE_RATE_HZ,
    )
    # Unlike LINEAR16, Google's MULAW output has no WAV header to strip —
    # it's already raw mulaw bytes.

    chunk_size = 1600  # ~200ms of 8kHz 8-bit mulaw audio per frame
    for i in range(0, len(audio), chunk_size):
        frame = audio[i:i + chunk_size]
        payload = base64.b64encode(frame).decode("ascii")
        await ws.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        }))
    await ws.send_text(json.dumps({
        "event": "mark",
        "streamSid": stream_sid,
        "mark": {"name": "reply-complete"},
    }))


@router.websocket("/twilio-stream")
async def twilio_stream(ws: WebSocket):
    # Local import to avoid a circular import: receptionist.py mounts
    # this adapter's router, so this adapter can't import receptionist
    # at module load time. By the time a call actually comes in, both
    # modules are fully loaded, so this is safe.
    from app.voice.receptionist import greeting_text, handle_turn
    from app.voice.session import clear_session

    await ws.accept()
    stream_sid: Optional[str] = None
    listener: Optional[TurnListener] = None
    listener_task = None

    async def start_new_turn():
        nonlocal listener, listener_task
        import asyncio
        listener = TurnListener(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=SAMPLE_RATE_HZ,
        )
        listener_task = asyncio.create_task(listener.get_transcript())

    try:
        while True:
            raw = await ws.receive_text()
            event = json.loads(raw)
            kind = event.get("event")

            if kind == "connected":
                continue

            elif kind == "start":
                stream_sid = event["start"]["streamSid"]
                await _send_tts_reply(ws, stream_sid, greeting_text())
                await start_new_turn()

            elif kind == "media" and listener is not None:
                payload_b64 = event["media"]["payload"]
                listener.push_audio(base64.b64decode(payload_b64))

                if listener_task.done():
                    transcript = listener_task.result()
                    _, reply_text, call_should_end = await handle_turn(stream_sid, transcript)
                    await _send_tts_reply(ws, stream_sid, reply_text)

                    if call_should_end:
                        await clear_session(stream_sid)
                        await ws.close()
                        return

                    await start_new_turn()

            elif kind == "mark":
                # Twilio echoes back our "reply-complete" marks; nothing
                # to do, but handled explicitly so it doesn't fall into
                # an unhandled-event branch.
                continue

            elif kind == "stop":
                if listener:
                    listener.close()
                if stream_sid:
                    await clear_session(stream_sid)
                break

    except WebSocketDisconnect:
        if listener:
            listener.close()
        # Session is intentionally left in Redis (not cleared) on an
        # unexpected disconnect, so a caller who redials can resume
        # where they left off.
