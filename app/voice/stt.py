"""
app/voice/stt.py

Provider-agnostic speech-to-text. Wraps Google Cloud Speech's
blocking streaming_recognize call in a background thread so it can
be awaited from asyncio. The audio encoding/sample rate are
parameters, not hardcoded — Exotel sends PCM16 @ 8kHz; a future
Twilio adapter would pass MULAW @ 8kHz instead. Adapters own the
audio format; this module just transcribes whatever they hand it.
"""

import asyncio
import queue
import time
from typing import Optional

from google.cloud import speech

DEFAULT_LANGUAGE_CODE = "en-IN"


class TurnListener:
    """
    Feed raw audio chunks via `push_audio`; call `get_transcript` once
    to block (off-thread) until Google's endpointer detects the caller
    has finished speaking (single_utterance=True) or a timeout hits.

    One instance = one caller turn. Create a new instance per turn.
    """

    def __init__(
        self,
        encoding: "speech.RecognitionConfig.AudioEncoding" = speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz: int = 8000,
        language_code: str = DEFAULT_LANGUAGE_CODE,
        timeout_s: float = 12.0,
    ):
        self._audio_q: "queue.Queue[Optional[bytes]]" = queue.Queue()
        self._client = speech.SpeechClient()
        self._config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate_hertz,
            language_code=language_code,
        )
        self._streaming_config = speech.StreamingRecognitionConfig(
            config=self._config,
            single_utterance=True,
            interim_results=False,
        )
        self._timeout_s = timeout_s

    def push_audio(self, chunk: bytes) -> None:
        self._audio_q.put(chunk)

    def close(self) -> None:
        self._audio_q.put(None)  # sentinel to stop the request generator

    def _run_blocking(self) -> str:
        deadline = time.monotonic() + self._timeout_s

        def request_gen():
            while time.monotonic() < deadline:
                try:
                    chunk = self._audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if chunk is None:
                    return
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        responses = self._client.streaming_recognize(
            config=self._streaming_config, requests=request_gen()
        )
        transcript = ""
        try:
            for response in responses:
                for result in response.results:
                    if result.is_final and result.alternatives:
                        transcript = result.alternatives[0].transcript
                        return transcript
        except Exception:
            # Network hiccup, endpointer timeout, etc. — fall through
            # with whatever we have (possibly empty) rather than
            # crashing the call.
            pass
        return transcript

    async def get_transcript(self) -> str:
        return await asyncio.to_thread(self._run_blocking)
