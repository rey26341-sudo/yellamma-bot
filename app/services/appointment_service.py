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
"""

import uuid

from app.database.database import session_scope
from app.models.appointment import Appointment


class AppointmentService:
    async def save_appointment(self, session: dict) -> Appointment:
        tenant_id_raw = session.get("tenant_id")
        if not tenant_id_raw:
            # Fail loudly rather than defaulting to some tenant (the
            # old code defaulted business_id to "salon" — a default
            # here would silently misfile a booking under the wrong
            # business, which is a data-integrity/privacy problem in
            # its own right).
            raise ValueError("save_appointment requires tenant_id in session")

        appointment = Appointment(
            tenant_id=uuid.UUID(tenant_id_raw),
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

        return appointment
