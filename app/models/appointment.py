from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String


class Base(DeclarativeBase):
    pass


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(String)

    name = Column(String)

    phone = Column(String)

    service = Column(String)

    date = Column(String)

    time = Column(String)
