"""
Ensures a Tenant row exists for each business config slug. Safe to
call on every startup — skips any slug that already has a row, so it
never duplicates or overwrites existing tenants.
"""
import asyncio
from sqlalchemy import select
from app.database.database import session_scope, init_models
from app.models.tenant import Tenant

BUSINESS_SLUGS = [
    ("medical_clinic", "NAX Medical Center"),
    ("dental_clinic", "NAX Dental Clinic"),
    ("physiotherapy", "NAX Physiotherapy"),
    ("beauty_salon", "Lustre Beauty Studio"),
    ("hair_salon", "NAX Hair Salon"),
    ("spa", "Serene Spa Retreat"),
    ("veterinary_clinic", "NAX Veterinary Clinic"),
    ("clinic_demo", "Demo Family Clinic"),
]


async def seed_tenants() -> None:
    # Ensures tables are created first in local/dev sqlite environments
    await init_models()

    async with session_scope() as db:
        for slug, name in BUSINESS_SLUGS:
            existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
            if existing.scalar_one_or_none():
                continue
            db.add(Tenant(slug=slug, name=name, plan="free", is_active=True))


if __name__ == "__main__":
    asyncio.run(seed_tenants())
