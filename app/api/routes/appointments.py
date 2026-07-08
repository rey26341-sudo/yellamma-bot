from fastapi import APIRouter
from app.database.database import SessionLocal
from app.models.appointment import Appointment

router = APIRouter()


@router.get("/appointments")
def get_appointments():

    db = SessionLocal()

    appointments = db.query(Appointment).all()

    result = []

    for appointment in appointments:
        result.append(
            {
                "id": appointment.id,
                "business_id": appointment.business_id,
                "name": appointment.name,
                "phone": appointment.phone,
                "service": appointment.service,
                "date": appointment.date,
                "time": appointment.time
            }
        )

    db.close()

    return result
