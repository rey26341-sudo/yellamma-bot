"""
Before: sync SessionLocal (no longer exists — database.py is async-
only now) and Appointment(business_id=...) (column no longer exists —
the model uses a real tenant_id FK now). This would have raised
ImportError on startup, then AttributeError/TypeError on the first
booking attempt even if the import were patched around.
Now: async, and takes tenant_id directly rather than resolving it —
callers (the save_appointment tool) already have the real tenant_id
from graph state, which itself came from the authenticated API key in
chat.py. No lookup-by-string happens anywhere in this path.

Also sends a Telegram notification to the business's configured
front-desk chat, if telegram_chat_id is set in that business's
config. Notification failures are logged but never block the booking
itself from succeeding — a saved appointment is the source of truth;
a missed notification is recoverable, a lost booking is not.
"""
import logging
import os
import uuid
import httpx
from app.database.database import session_scope
from app.models.appointment import Appointment
from app.services.config_loader import load_config

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


async def _notify_telegram(business_id: str, appointment: Appointment) -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set; skipping notification")
        return
    try:
        config = load_config(business_id)
    except FileNotFoundError:
        logger.warning("No config found for %r; skipping notification", business_id)
        return

    chat_id = config.get("telegram_chat_id")
    if not chat_id:
        return

    business_name = config.get("business_name", business_id)
    text = (
        f"New appointment — {business_name}\n\n"
        f"Name: {appointment.name}\n"
        f"Phone: {appointment.phone}\n"
        f"Service: {appointment.service}\n"
        f"Date: {appointment.date}\n"
        f"Time: {appointment.time}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
            resp.raise_for_status()
    except Exception:
        logger.exception("Failed to send Telegram notification for %r", business_id)


class AppointmentService:
    async def save_appointment(self, session: dict) -> Appointment:
        tenant_id_raw = session.get("tenant_id")
        if not tenant_id_raw:
            raise ValueError("save_appointment requires tenant_id in session")
        appointment = Appointment(
            tenant_id=int(tenant_id_raw),
            business_id=session.get("business_id") or "",
            name=session.get("name"),
            phone=session.get("phone"),
            service=session.get("service") or "Not specified",
            date=session.get("date"),
            time=session.get("time"),
        )
        async with session_scope() as db:
            db.add(appointment)
            await db.flush()
            await db.refresh(appointment)

        business_id = session.get("business_id")
        if business_id:
            await _notify_telegram(business_id, appointment)

        return appointment
