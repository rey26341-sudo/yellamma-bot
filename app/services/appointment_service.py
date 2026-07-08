from app.database.database import SessionLocal
from app.models.appointment import Appointment


class AppointmentService:

    def save_appointment(self, session):

        db = SessionLocal()

        appointment = Appointment(
            business_id=session.get("business_id", "salon"),
            name=session.get("name"),
            phone=session.get("phone"),
            service=session.get("service", "Not specified"),
            date=session.get("date"),
            time=session.get("time")
        )

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        db.close()

        return appointment
