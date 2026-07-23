"""
app/channels/base.py

Provider-agnostic channel interfaces. The LangGraph core
(app/core/graph.py) never imports anything from this file or its
subclasses — it only ever receives a plain `message` string and a
`session_id`, and returns a `reply` string. Adapters are the
translation layer between a specific provider's wire format and that
plain interface, exactly the same pattern already used for voice
(app/voice/adapters/exotel.py, twilio.py).

No provider is chosen yet for WhatsApp — see the TODO subclasses
below. Website chat (app/api/routes/chat.py) and voice already have
their own adapters; this file adds the interface WhatsApp
implementations will conform to once a provider (Meta Cloud API,
Twilio, 360dialog, etc.) is picked.
"""

from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    """Base interface every channel adapter implements."""

    @abstractmethod
    async def send_message(self, recipient: str, text: str) -> None:
        """Send `text` to `recipient` over this channel."""
        raise NotImplementedError


class WhatsAppAdapter(ChannelAdapter):
    """
    Base class for WhatsApp-specific adapters. `recipient` is a phone
    number in whatever format the concrete provider expects (e.g.
    E.164 for Meta's Cloud API).
    """

    @abstractmethod
    async def send_message(self, recipient: str, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def handle_incoming(self, payload: dict) -> tuple[str, str]:
        """
        Parse a provider-specific incoming-webhook payload into
        (sender_phone, message_text) — the two things the LangGraph
        core actually needs. Each provider's webhook JSON shape is
        different; this is where that gets normalized away.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------
# TODO: pick a provider before implementing any of these. Each one is
# a real implementation, not a formality — Meta's Cloud API, Twilio's
# WhatsApp API, and 360dialog all have meaningfully different auth,
# payload shapes, and rate limits. Implement only the one(s) you
# actually need.
#
# class MetaWhatsAppAdapter(WhatsAppAdapter):
#     ...
#
# class TwilioWhatsAppAdapter(WhatsAppAdapter):
#     ...
#
# class ThreeSixtyDialogWhatsAppAdapter(WhatsAppAdapter):
#     ...
# ---------------------------------------------------------------------
