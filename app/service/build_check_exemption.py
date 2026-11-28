from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.database.torii_sub_profile import ToriiSubProfile

EXEMPT_ACCOUNT_IDS = frozenset({3, 349})


async def is_build_check_exempt(db: AsyncSession, user_id: int) -> bool:
    if user_id <= 0:
        return False
    roots = EXEMPT_ACCOUNT_IDS | set(getattr(settings, "client_check_exempt_user_ids", []))
    if user_id in roots:
        return True
    master_id = (await db.exec(select(ToriiSubProfile.master_user_id).where(
        ToriiSubProfile.profile_user_id == user_id,
        col(ToriiSubProfile.master_user_id).in_(roots),
    ))).first()
    return master_id is not None
