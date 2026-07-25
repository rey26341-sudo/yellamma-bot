from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    tenant_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )

    business_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    service: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    date: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    time: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
