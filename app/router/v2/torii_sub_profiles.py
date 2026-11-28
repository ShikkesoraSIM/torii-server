import json
import re
import secrets
from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import HTTPException, Query, Security, status
from pydantic import BaseModel, Field
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import create_access_token, get_password_hash
from app.config import settings
from app.database.statistics import UserStatistics, get_rank
from app.database.torii_sub_profile import ProfileRestrictionMode, ToriiSubProfile
from app.database.user import User
from app.dependencies.database import Database
from app.dependencies.user import get_current_user
from app.log import logger
from app.models.score import GameMode
from app.models.mods import API_MODS
from app.models.sub_profile_mod_policy import validate_policy
from app.models.torii_points import PointReason
from app.router.auth import generate_refresh_token, store_token
from app.service import points_service
from app.utils import utcnow

from .router import router

EXTRA_SLOT_PRICE = 5000


class CreateSubProfileRequest(BaseModel):
    request_id: UUID
    expected_cost: int = Field(..., ge=0)
    name: str = Field(..., min_length=2, max_length=32, description="Nombre descriptivo del perfil")
    tag: str = Field(..., min_length=2, max_length=8, description="Tag identificador, ej: DT, HD, NM")
    restriction_mode: ProfileRestrictionMode = Field(default=ProfileRestrictionMode.FREE, description="free, hd_only, dt_only, nomod_only, custom")
    required_mods: list[str] = Field(default_factory=list, description="Lista de siglas de mods requeridos (para modo custom)")
    allowed_mods: list[str] = Field(default_factory=list, description="Lista de siglas de mods permitidos (para modo custom)")
    disallowed_mods: list[str] = Field(default_factory=list, description="Lista de siglas de mods prohibidos (para modo custom)")
    mod_policy: dict | None = None
    ruleset_id: Literal[0, 1, 2, 3] = 0


class SwitchProfileResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    profile_user_id: int
    master_user_id: int
    username: str
    name: str
    tag: str
    restriction_mode: str


async def resolve_master_user_id(db: AsyncSession, user_id: int) -> int:
    """Si user_id es un sub-perfil persona, devuelve el master_user_id. Si no, devuelve user_id."""
    sub_profile = (
        await db.exec(
            select(ToriiSubProfile.master_user_id).where(ToriiSubProfile.profile_user_id == user_id)
        )
    ).first()
    return int(sub_profile) if sub_profile else user_id


@router.get("/torii/sub-profiles", tags=["Torii Sub-Profiles"])
async def get_my_sub_profiles(
    current_user: Annotated[User, Security(get_current_user, scopes=["*"])],
    db: Database,
    ruleset_id: int = Query(0, ge=0, le=3),
):
    """
    Lista todos los sub-perfiles asociados a la cuenta principal del usuario logueado,
    incluyendo stats resumidas (PP, rango, precisión, playcount) y el costo del siguiente slot.
    """
    master_id = await resolve_master_user_id(db, current_user.id)
    master_user = await db.get(User, master_id)
    if not master_user:
        raise HTTPException(status_code=404, detail="Usuario maestro no encontrado.")

    sub_profiles = (
        await db.exec(
            select(ToriiSubProfile)
            .where(ToriiSubProfile.master_user_id == master_id)
            .where(ToriiSubProfile.ruleset_id == ruleset_id)
            .order_by(ToriiSubProfile.created_at.asc())
        )
    ).all()

    all_user_ids = [master_id] + [p.profile_user_id for p in sub_profiles]

    stats_rows = (
        await db.exec(
            select(UserStatistics)
            .where(
                col(UserStatistics.user_id).in_(all_user_ids),
                UserStatistics.mode == GameMode.from_int(ruleset_id),
            )
        )
    ).all()
    stats_by_user = {s.user_id: s for s in stats_rows}

    users_rows = (
        await db.exec(select(User).where(col(User.id).in_(all_user_ids)))
    ).all()
    users_by_id = {u.id: u for u in users_rows}

    master_stats = stats_by_user.get(master_id)
    profiles_data = [
        {
            "id": 0,
            "profile_user_id": master_id,
            "master_user_id": master_id,
            "name": "Main",
            "tag": "MAIN",
            "username": master_user.username,
            "restriction_mode": "free",
            "ruleset_id": ruleset_id,
            "required_mods": [],
            "allowed_mods": [],
            "disallowed_mods": [],
            "is_master": True,
            "is_active": current_user.id == master_id,
            "pp": float(master_stats.pp) if master_stats and master_stats.pp else 0.0,
            "global_rank": int(await get_rank(db, master_stats) or 0) if master_stats else 0,
            "accuracy": float(master_stats.hit_accuracy) if master_stats else 0.0,
            "play_count": int(master_stats.play_count) if master_stats and master_stats.play_count else 0,
            "avatar_url": master_user.avatar_url,
            "created_at": master_user.join_date.isoformat() if master_user.join_date else None,
        }
    ]

    for p in sub_profiles:
        p_user = users_by_id.get(p.profile_user_id)
        p_stats = stats_by_user.get(p.profile_user_id)
        profiles_data.append(
            {
                "id": p.id,
                "profile_user_id": p.profile_user_id,
                "master_user_id": master_id,
                "name": p.name,
                "tag": p.tag,
                "username": p_user.username if p_user else p.name,
                "restriction_mode": p.restriction_mode,
                "ruleset_id": p.ruleset_id,
                "mod_policy": json.loads(p.mod_policy) if p.mod_policy else None,
                "required_mods": p.get_required_mods_list(),
                "allowed_mods": p.get_allowed_mods_list(),
                "disallowed_mods": p.get_disallowed_mods_list(),
                "is_master": False,
                "is_active": current_user.id == p.profile_user_id,
                "pp": float(p_stats.pp) if p_stats and p_stats.pp else 0.0,
                "global_rank": int(await get_rank(db, p_stats) or 0) if p_stats else 0,
                "accuracy": float(p_stats.hit_accuracy) if p_stats else 0.0,
                "play_count": int(p_stats.play_count) if p_stats and p_stats.play_count else 0,
                "avatar_url": p_user.avatar_url if p_user else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    points_balance = await points_service.get_balance(db, master_id)
    sub_profiles_count = (await db.exec(select(func.count(ToriiSubProfile.id)).where(ToriiSubProfile.master_user_id == master_id))).one() or 0
    next_slot_cost = 0 if sub_profiles_count == 0 else EXTRA_SLOT_PRICE

    return {
        "master_user_id": master_id,
        "active_profile_user_id": current_user.id,
        "profiles": profiles_data,
        "total_profiles": len(profiles_data),
        "user_points": points_balance,
        "next_slot_cost": next_slot_cost,
    }


@router.get("/torii/profiles/{user_id}", tags=["Torii Sub-Profiles"])
async def get_public_profiles(user_id: int, db: Database, mode: GameMode = GameMode.OSU):
    viewed_user = await db.get(User, user_id)
    if viewed_user is None or await viewed_user.is_restricted(db):
        raise HTTPException(status_code=404, detail="User not found.")
    master_id = await resolve_master_user_id(db, user_id)
    profiles = (await db.exec(select(ToriiSubProfile).where(
        ToriiSubProfile.master_user_id == master_id,
        ToriiSubProfile.ruleset_id == int(mode),
    ).order_by(ToriiSubProfile.created_at.asc()))).all()
    ids = [master_id] + [p.profile_user_id for p in profiles]
    users = (await db.exec(select(User).where(
        col(User.id).in_(ids), ~User.is_restricted_query(User.id),
    ))).all()
    visible = {u.id: u for u in users}
    if master_id not in visible:
        raise HTTPException(status_code=404, detail="User not found.")
    stats = (await db.exec(select(UserStatistics).where(
        col(UserStatistics.user_id).in_(list(visible)), UserStatistics.mode == mode,
    ))).all()
    by_id = {s.user_id: s for s in stats}

    async def entry(profile_user_id, name, is_main):
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
        "mode": str(mode),
        "profiles": [await entry(master_id, "Main", True)] + [
            await entry(p.profile_user_id, p.name, False) for p in profiles if p.profile_user_id in visible
        ],
    }


@router.post("/torii/sub-profiles", tags=["Torii Sub-Profiles"], status_code=status.HTTP_201_CREATED)
async def create_sub_profile(
    body: CreateSubProfileRequest,
    current_user: Annotated[User, Security(get_current_user, scopes=["*"])],
    db: Database,
):
    """
    Crea un nuevo sub-perfil persona para el usuario actual.
    El primer perfil es gratis; los siguientes cuestan 5,000 monedas.
    """
    master_id = await resolve_master_user_id(db, current_user.id)
    master_user = (await db.exec(select(User).where(User.id == master_id)
                                 .with_for_update().execution_options(populate_existing=True))).first()
    if not master_user:
        raise HTTPException(status_code=404, detail="Master user not found.")
    if await master_user.is_restricted(db):
        raise HTTPException(status_code=403, detail="This account is restricted.")

    existing = (await db.exec(select(ToriiSubProfile).where(
        ToriiSubProfile.creation_key == str(body.request_id),
    ).with_for_update())).first()
    if existing is not None:
        if existing.master_user_id != master_id:
            raise HTTPException(status_code=409, detail="This creation request is already in use.")
        if existing.name != body.name or existing.tag != re.sub(r"[^A-Za-z0-9]", "", body.tag).upper() \
                or (json.loads(existing.mod_policy) if existing.mod_policy else None) != body.mod_policy:
            raise HTTPException(status_code=409, detail="This request already created a profile. Reopen the form to create another.")
        target_user = await db.get(User, existing.profile_user_id)
        if target_user is None or await target_user.is_restricted(db):
            raise HTTPException(status_code=403, detail="This profile is unavailable.")
        return await issue_profile_session(db, target_user, existing)

    policy = None
    if body.mod_policy is not None:
        if body.restriction_mode != ProfileRestrictionMode.CUSTOM:
            raise HTTPException(status_code=400, detail="Configured mods require a custom profile.")
        try:
            policy = validate_policy(body.mod_policy, API_MODS)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    clean_tag = re.sub(r"[^A-Za-z0-9]", "", body.tag).upper()
    if not clean_tag or len(clean_tag) < 2:
        raise HTTPException(status_code=400, detail="Tag must contain at least 2 alphanumeric characters (e.g. DT, HD, NM).")

    existing_count = len((await db.exec(select(ToriiSubProfile.id).where(
        ToriiSubProfile.master_user_id == master_id,
    ).with_for_update())).all())
    cost = 0 if existing_count == 0 else EXTRA_SLOT_PRICE
    if body.expected_cost != cost:
        raise HTTPException(status_code=409, detail="The profile price changed. Reopen the form before confirming.")

    if existing_count >= 1:
        balance = await points_service.get_balance(db, master_id)
        if balance < EXTRA_SLOT_PRICE:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Additional profile slots cost {EXTRA_SLOT_PRICE} coins (current balance: {balance}).",
            )
        spent_ok = await points_service.spend(
            db,
            master_id,
            EXTRA_SLOT_PRICE,
            PointReason.STORE_PURCHASE,
            ref=f"sub_profile:{clean_tag}",
        )
        if not spent_ok:
            raise HTTPException(status_code=400, detail="Failed to spend coins for the new profile.")

    suffix = f" [{clean_tag}]"
    base_shadow_name = f"{master_user.username[:32 - len(suffix)]}{suffix}"
    candidate_name = base_shadow_name
    counter = 2
    while (await db.exec(select(User.id).where(User.username == candidate_name))).first() is not None:
        suffix = f" [{clean_tag}{counter}]"
        candidate_name = f"{master_user.username[:32 - len(suffix)]}{suffix}"
        counter += 1

    shadow_email = f"profile-{body.request_id}@profiles.torii.invalid"

    shadow_user = User(
        username=candidate_name,
        email=shadow_email,
        pw_bcrypt=get_password_hash(secrets.token_urlsafe(32)),
        priv=1,
        country_code=master_user.country_code,
        join_date=utcnow(),
        last_visit=utcnow(),
        avatar_url=master_user.avatar_url,
        is_supporter=master_user.is_supporter,
        support_level=master_user.support_level,
    )
    db.add(shadow_user)
    await db.flush()

    for mode in (GameMode.OSU, GameMode.TAIKO, GameMode.FRUITS, GameMode.MANIA):
        db.add(UserStatistics(mode=mode, user_id=shadow_user.id))
    if settings.enable_rx:
        for mode in (GameMode.OSURX, GameMode.TAIKORX, GameMode.FRUITSRX):
            db.add(UserStatistics(mode=mode, user_id=shadow_user.id))
    if settings.enable_ap:
        db.add(UserStatistics(mode=GameMode.OSUAP, user_id=shadow_user.id))

    sub_profile = ToriiSubProfile(
        master_user_id=master_id,
        profile_user_id=shadow_user.id,
        name=body.name,
        tag=clean_tag,
        restriction_mode=body.restriction_mode,
        required_mods=json.dumps([m.upper() for m in body.required_mods]),
        allowed_mods=json.dumps([m.upper() for m in body.allowed_mods]),
        disallowed_mods=json.dumps([m.upper() for m in body.disallowed_mods]),
        mod_policy=json.dumps(policy) if policy is not None else None,
        ruleset_id=policy["ruleset_id"] if policy is not None else body.ruleset_id,
        creation_key=str(body.request_id),
        created_at=utcnow(),
    )
    db.add(sub_profile)
    await db.flush()

    logger.info(
        "[SubProfile] Created persona profile_user_id={} master_user_id={} name='{}' tag='{}' mode='{}'",
        shadow_user.id,
        master_id,
        body.name,
        clean_tag,
        body.restriction_mode,
    )

    return await issue_profile_session(db, shadow_user, sub_profile)


async def issue_profile_session(db: AsyncSession, target_user: User, profile: ToriiSubProfile | None):
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(data={"sub": str(target_user.id)}, expires_delta=access_token_expires)
    refresh_token_str = generate_refresh_token()
    response = {
        "id": profile.id if profile else 0,
        "profile_user_id": target_user.id,
        "master_user_id": profile.master_user_id if profile else target_user.id,
        "name": profile.name if profile else "Main",
        "tag": profile.tag if profile else "MAIN",
        "username": target_user.username,
        "restriction_mode": profile.restriction_mode if profile else "free",
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "expires_in": settings.access_token_expire_minutes * 60,
        "token_type": "Bearer",
    }
    await store_token(
        db,
        target_user.id,
        settings.osu_client_id,
        ["*"],
        access_token,
        refresh_token_str,
        settings.access_token_expire_minutes * 60,
        settings.refresh_token_expire_minutes * 60,
        allow_multiple_devices=True,
    )

    return response


@router.post("/torii/sub-profiles/{profile_id}/switch", tags=["Torii Sub-Profiles"], response_model=SwitchProfileResponse)
async def switch_to_sub_profile(
    profile_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["*"])],
    db: Database,
):
    """
    Emite un token de sesión OAuth para cambiar activamente al perfil seleccionado.
    El perfil debe pertenecer a la cuenta maestra del usuario.
    """
    master_id = await resolve_master_user_id(db, current_user.id)

    target_profile = (
        await db.exec(
            select(ToriiSubProfile)
            .where(
                ToriiSubProfile.id == profile_id,
                ToriiSubProfile.master_user_id == master_id,
            )
        )
    ).first()

    if not target_profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado o no pertenece a tu cuenta.")

    target_user = await db.get(User, target_profile.profile_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario del perfil no encontrado.")
    if await target_user.is_restricted(db):
        raise HTTPException(status_code=403, detail="This profile is restricted.")

    logger.info(
        "[SubProfile] User {} switched to persona {} ({})",
        current_user.id,
        target_user.id,
        target_profile.name,
    )

    return await issue_profile_session(db, target_user, target_profile)


@router.post("/torii/sub-profiles/switch-master", tags=["Torii Sub-Profiles"], response_model=SwitchProfileResponse)
async def switch_to_master(
    current_user: Annotated[User, Security(get_current_user, scopes=["*"])],
    db: Database,
):
    """
    Emite un token de sesión OAuth para volver a la cuenta Principal (Master).
    """
    master_id = await resolve_master_user_id(db, current_user.id)
    master_user = await db.get(User, master_id)
    if not master_user:
        raise HTTPException(status_code=404, detail="Usuario maestro no encontrado.")
    if await master_user.is_restricted(db):
        raise HTTPException(status_code=403, detail="This account is restricted.")

    logger.info("[SubProfile] User {} switched back to master {}", current_user.id, master_id)

    return await issue_profile_session(db, master_user, None)
