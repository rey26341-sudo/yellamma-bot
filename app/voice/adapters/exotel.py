"""
app/voice/adapters/exotel.py

Exotel-specific adapter. This is the ONLY module that should know
about Exotel's WebSocket event shapes (stream_sid, media.payload,
PCM16 @ 8kHz) or its Voicebot/Passthru Applet conventions. It
translates Exotel's audio stream into STT transcripts, hands each
transcript to the provider-agnostic conversation core
(`app.voice.receptionist.handle_turn`), and turns the reply back into
Exotel-formatted audio via TTS.

A future Twilio adapter (app/voice/adapters/twilio.py) would mirror
this file's shape but speak Twilio Media Streams' event format
(streamSid, MULAW @ 8kHz) instead — the conversation core wouldn't
change at all.
"""

import base64
import json
from typing import Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from google.cloud import speech, texttospeech

from app.voice.stt import TurnListener
from app.voice.tts import synthesize_speech

router = APIRouter()

SAMPLE_RATE_HZ = 8000  # Exotel's required PCM sample rate


# ---------------------------------------------------------------------
# Dynamic WebSocket URL endpoint — configure this URL in the Voicebot
# Applet's "dynamic" HTTPS mode instead of a static wss:// address if
# you need per-call routing (e.g. per-clinic).
# ---------------------------------------------------------------------

@router.get("/connect")
@router.post("/connect")
async def connect_voicebot(request: Request):
    host = request.headers.get("host", "your-domain.example.com")
    return JSONResponse({"url": f"wss://{host}/voice/stream"})


async def _send_tts_reply(ws: WebSocket, stream_sid: str, text: str) -> None:
    """Synthesize `text` and stream it back to Exotel as media events."""
    pcm = await synthesize_speech(
        text,
        encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE_HZ,
    )
    # Strip the 44-byte WAV header Google returns for LINEAR16 output,
    # since Exotel expects raw PCM frames, not a WAV container.
    raw_pcm = pcm[44:] if pcm[:4] == b"RIFF" else pcm

    chunk_size = 3200  # ~100ms of 8kHz 16-bit mono audio, per Exotel guidance
    for i in range(0, len(raw_pcm), chunk_size):
        frame = raw_pcm[i:i + chunk_size]
        payload = base64.b64encode(frame).decode("ascii")
        await ws.send_text(json.dumps({
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"payload": payload},
        }))
    await ws.send_text(json.dumps({
        "event": "mark",
        "stream_sid": stream_sid,
        "mark": {"name": "reply-complete"},
    }))


@router.websocket("/stream")
async def voice_stream(ws: WebSocket):
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
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
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
                stream_sid = event["stream_sid"]
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

            elif kind == "dtmf":
                # Let callers press 0 to reach a human.
                digit = event.get("dtmf", {}).get("digit")
                if digit == "0" and stream_sid:
                    await _send_tts_reply(
                        ws, stream_sid,
                        "Connecting you to our front desk team. Please hold."
                    )
                    await clear_session(stream_sid)
                    await ws.close()
                    return

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


# ---------------------------------------------------------------------
# Passthru applet — runs right after the Voicebot applet disconnects.
# Use this to route the call onward (e.g. escalate to a human agent)
# based on how the conversation ended.
# ---------------------------------------------------------------------

@router.get("/passthru")
async def voice_passthru(request: Request):
    call_sid = request.query_params.get("CallSid")
    # TODO: look up how the call ended (e.g. a flag set during /stream)
    # and return routing info your App Bazaar flow expects.
    return JSONResponse({"status": "ok", "call_sid": call_sid})
