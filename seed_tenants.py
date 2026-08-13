"""One-time script: create a Tenant row for each business config slug."""
import asyncio
from app.database.database import session_scope
from app.models.tenant import Tenant
from sqlalchemy import select

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

async def main():
    async with session_scope() as db:
        for slug, name in BUSINESS_SLUGS:
            existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
            if existing.scalar_one_or_none():
                print(f"skip (exists): {slug}")
                continue
            db.add(Tenant(slug=slug, name=name, plan="free", is_active=True))
            print(f"created: {slug}")

if __name__ == "__main__":
    asyncio.run(main())
