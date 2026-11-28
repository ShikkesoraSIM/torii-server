from fastapi import HTTPException
from sqlmodel import col, select

from app.database.statistics import UserStatistics, get_rank
from app.database.torii_sub_profile import ToriiSubProfile
from app.database.user import User
from app.dependencies.database import Database
from app.models.score import GameMode

from .router import router


@router.get("/torii/profiles/{user_id}", tags=["Torii profiles"])
async def get_public_profiles(user_id: int, db: Database, mode: GameMode = GameMode.OSU):
    viewed_user = await db.get(User, user_id)
    if viewed_user is None or await viewed_user.is_restricted(db):
        raise HTTPException(status_code=404, detail="User not found.")

    membership = (await db.exec(select(ToriiSubProfile.master_user_id).where(
        ToriiSubProfile.profile_user_id == user_id,
    ))).first()
    master_id = int(membership) if membership is not None else user_id
    family = (await db.exec(select(ToriiSubProfile).where(
        ToriiSubProfile.master_user_id == master_id,
    ).order_by(ToriiSubProfile.created_at.asc()))).all()
    # Los perfiles viejos eran de standard; no mostrarlos en otros modos.
    profiles = [profile for profile in family if getattr(profile, "ruleset_id", 0) == int(mode)]
    ids = [master_id] + [profile.profile_user_id for profile in profiles]
    users = (await db.exec(select(User.id).where(
        col(User.id).in_(ids), ~User.is_restricted_query(User.id),
    ))).all()
    visible = set(users)
    if master_id not in visible:
        raise HTTPException(status_code=404, detail="User not found.")

    stats = (await db.exec(select(UserStatistics).where(
        col(UserStatistics.user_id).in_(visible), UserStatistics.mode == mode,
    ))).all()
    by_id = {stat.user_id: stat for stat in stats}

    async def entry(profile_user_id: int, name: str, is_main: bool):
        stat = by_id.get(profile_user_id)
        return {
            "user_id": profile_user_id,
            "name": name,
            "is_main": is_main,
            "pp": float(stat.pp or 0) if stat else 0,
            "global_rank": int(await get_rank(db, stat) or 0) if stat else 0,
        }

    return {
        "master_user_id": master_id,
        "mode": mode.value,
        "profiles": [await entry(master_id, "Main", True)] + [
            await entry(profile.profile_user_id, profile.name, False)
            for profile in profiles if profile.profile_user_id in visible
        ],
    }
