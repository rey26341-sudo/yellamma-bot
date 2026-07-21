"""
app/voice/tts.py

Provider-agnostic text-to-speech. Wraps Google Cloud Text-to-Speech.
Encoding/sample rate are parameters so each adapter can request the
raw audio format its telephony provider needs — Exotel wants PCM16 @
8kHz; a future Twilio adapter would request MULAW @ 8kHz instead.
"""

import asyncio
from typing import Optional

from google.cloud import texttospeech

DEFAULT_LANGUAGE_CODE = "en-IN"
# Chirp 3: HD is Google's newest, most natural-sounding voice tier —
# noticeably calmer and less "announcement-y" than the older Neural2
# tier this used to default to. Aoede tested best for a calm, gentle
# clinic-receptionist feel — Kore, Leda, and Achernar all also sound
# good if you want to switch things up later.
DEFAULT_VOICE_NAME = "en-IN-Chirp3-HD-Aoede"

_tts_client: Optional[texttospeech.TextToSpeechClient] = None


def _get_client() -> texttospeech.TextToSpeechClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def _synthesize_blocking(
    text: str,
    encoding: "texttospeech.AudioEncoding",
    sample_rate_hertz: int,
    language_code: str,
    voice_name: str,
) -> bytes:
    client = _get_client()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )
    # Chirp 3: HD voices don't support the `pitch` parameter (only
    # older tiers like Neural2/WaveNet/Standard do) — setting it would
    # be silently ignored at best. speaking_rate works across all
    # tiers, so it's kept for a slightly slower, calmer pace.
    is_chirp3_hd = "Chirp3-HD" in voice_name
    audio_config_kwargs = dict(
        audio_encoding=encoding,
        sample_rate_hertz=sample_rate_hertz,
        speaking_rate=0.95,  # slightly slower — calmer, easier to follow
    )
    if not is_chirp3_hd:
        audio_config_kwargs["pitch"] = -1.0  # a touch lower/softer
    audio_config = texttospeech.AudioConfig(**audio_config_kwargs)

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content


async def synthesize_speech(
    text: str,
    encoding: "texttospeech.AudioEncoding" = texttospeech.AudioEncoding.LINEAR16,
    sample_rate_hertz: int = 8000,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
) -> bytes:
    """
    Returns raw audio bytes in the requested encoding. Note: Google
    wraps LINEAR16 output in a 44-byte WAV header — callers that need
    truly raw PCM (like the Exotel adapter) must strip it themselves;
    MULAW/other encodings are returned header-free.
    """
    return await asyncio.to_thread(
        _synthesize_blocking, text, encoding, sample_rate_hertz, language_code, voice_name
    )
