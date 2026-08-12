from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.appointment import Appointment

router = APIRouter()


@router.get("/appointments")
async def get_appointments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment))
    appointments = result.scalars().all()

    return [
        {
            "id": appointment.id,
            "business_id": appointment.business_id,
            "name": appointment.name,
            "phone": appointment.phone,
            "service": appointment.service,
            "date": appointment.date,
            "time": appointment.time,
        }
        for appointment in appointments
    ]
