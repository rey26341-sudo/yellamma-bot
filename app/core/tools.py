"""
app/core/tools.py

LangChain tools the graph can call. Wraps the existing
AppointmentService rather than reimplementing it — the DB write logic
(SQLAlchemy session, Appointment model) is unchanged from before.
"""

from langchain_core.tools import tool

from app.services.appointment_service import AppointmentService

_appointment_service = AppointmentService()


@tool
def save_appointment(
    business_id: str,
    name: str,
    phone: str,
    service: str,
    date: str,
    time: str,
) -> str:
    """
    Save a completed appointment booking to the database. Call this
    only once name, phone, date, and time have all been collected
    from the customer.
    """
    session_dict = {
        "business_id": business_id,
        "name": name,
        "phone": phone,
        "service": service or "Not specified",
        "date": date,
        "time": time,
    }
    appointment = _appointment_service.save_appointment(session_dict)
    return f"Appointment saved with id={appointment.id}"


# TODO (Phase 2): add tools for SMS/WhatsApp confirmation sends here,
# each calling a ChannelAdapter.send_message(phone, text) — see
# app/channels/base.py. Left out for now since no WhatsApp provider
# has been chosen yet.
