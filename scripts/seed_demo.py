"""Seed a demo user + project for sales demos and integration tests.

Idempotent: re-running is safe and updates the password to the seeded value.

    docker compose run --rm api python /app/scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from tcvn_copilot.core.logging import configure_logging, get_logger
from tcvn_copilot.core.security import hash_password
from tcvn_copilot.db.models.project import BuildingType, Project
from tcvn_copilot.db.models.user import User
from tcvn_copilot.db.session import async_session_factory, dispose_engine, init_engine

DEMO_EMAIL = "demo@tcvn-copilot.dev"
DEMO_PASSWORD = "demo-pw-please-change-123!"


async def main() -> int:
    configure_logging()
    log = get_logger(__name__)
    init_engine()

    async with async_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                full_name="Demo Engineer",
                password_hash=hash_password(DEMO_PASSWORD),
                organization="Demo Co.",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            log.info("seeded_user", email=user.email)
        else:
            user.password_hash = hash_password(DEMO_PASSWORD)
            log.info("reset_demo_user_password", email=user.email)

        project = await session.scalar(
            select(Project).where(Project.owner_id == user.id, Project.name == "Hùng Vương Tower")
        )
        if project is None:
            session.add(
                Project(
                    name="Hùng Vương Tower",
                    description="Demo project — 22-storey office tower for showcase reviews.",
                    building_type=BuildingType.OFFICE,
                    location="Hà Nội",
                    owner_id=user.id,
                )
            )
            log.info("seeded_project", name="Hùng Vương Tower")

        await session.commit()
    await dispose_engine()

    print(f"✅ demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
