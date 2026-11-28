"""POST /api/v2/torii/settings-telemetry — anonymous settings usage ingest.

Accepts an anonymous configuration snapshot keyed by a salted client-generated
``install_hash`` (SHA-256 hex, 16..64 chars) and upserts one row per install in
``torii_settings_telemetry``. Never stores user IDs, IPs, file paths, or PII.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.database.torii_settings_telemetry import ToriiSettingsTelemetry
from app.dependencies.database import Database
from app.utils import utcnow

from .router import router


MAX_SETTINGS_KEYS = 80
MAX_KEY_LEN = 64
MAX_STR_VAL_LEN = 64
_SAFE_KEY_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")
_HEX_RE = re.compile(r"^[a-fA-F0-9]{16,64}$")


class SettingsTelemetryRequest(BaseModel):
    install_hash: str = Field(min_length=16, max_length=64)
    app_version: str | None = Field(default=None, max_length=48)
    stream: str | None = Field(default=None, max_length=24)
    platform: str | None = Field(default=None, max_length=32)
    cpu_arch: str | None = Field(default=None, max_length=16)

    ui_theme: str | None = Field(default=None, max_length=32)
    classic_enabled: bool = False
    nsfw_enabled: bool = False
    open_folders_skins: bool = False
    open_folders_songs: bool = False
    potato_mode: bool = False
    lightweight_interface: bool = False
    renderer: str | None = Field(default=None, max_length=32)
    audio_mode: str | None = Field(default=None, max_length=32)

    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("install_hash")
    @classmethod
    def _validate_hash(cls, v: str) -> str:
        v = v.strip().lower()
        if not _HEX_RE.match(v):
            raise ValueError("install_hash must be 16-64 hex characters")
        return v

    @field_validator("settings")
    @classmethod
    def _sanitize_settings(cls, v: dict[str, Any]) -> dict[str, bool | int | float | str]:
        cleaned: dict[str, bool | int | float | str] = {}
        for k, val in v.items():
            if len(cleaned) >= MAX_SETTINGS_KEYS:
                break
            if not isinstance(k, str) or not _SAFE_KEY_RE.match(k):
                continue
            if isinstance(val, bool):
                cleaned[k] = val
            elif isinstance(val, (int, float)):
                cleaned[k] = val
            elif isinstance(val, str):
                cleaned[k] = val[:MAX_STR_VAL_LEN]
        return cleaned


class SettingsTelemetryResponse(BaseModel):
    ok: bool = True


@router.post(
    "/torii/settings-telemetry",
    tags=["Torii"],
    response_model=SettingsTelemetryResponse,
    name="Submit anonymous Torii settings telemetry snapshot",
    description=(
        "Upserts the latest anonymous settings snapshot for a Torii client installation. "
        "No user authentication or PII is stored; only bounded enum/bool configuration flags."
    ),
)
async def submit_settings_telemetry(
    body: SettingsTelemetryRequest,
    session: Database,
) -> SettingsTelemetryResponse:
    now = utcnow()
    existing = await session.get(ToriiSettingsTelemetry, body.install_hash)

    if existing is None:
        row = ToriiSettingsTelemetry(
            install_hash=body.install_hash,
            first_seen_at=now,
            updated_at=now,
            app_version=body.app_version,
            stream=body.stream,
            platform=body.platform,
            cpu_arch=body.cpu_arch,
            ui_theme=body.ui_theme,
            classic_enabled=body.classic_enabled,
            nsfw_enabled=body.nsfw_enabled,
            open_folders_skins=body.open_folders_skins,
            open_folders_songs=body.open_folders_songs,
            potato_mode=body.potato_mode,
            lightweight_interface=body.lightweight_interface,
            renderer=body.renderer,
            audio_mode=body.audio_mode,
            settings_json=body.settings,
        )
        session.add(row)
    else:
        existing.updated_at = now
        existing.app_version = body.app_version
        existing.stream = body.stream
        existing.platform = body.platform
        existing.cpu_arch = body.cpu_arch
        existing.ui_theme = body.ui_theme
        existing.classic_enabled = body.classic_enabled
        existing.nsfw_enabled = body.nsfw_enabled
        existing.open_folders_skins = body.open_folders_skins
        existing.open_folders_songs = body.open_folders_songs
        existing.potato_mode = body.potato_mode
        existing.lightweight_interface = body.lightweight_interface
        existing.renderer = body.renderer
        existing.audio_mode = body.audio_mode
        existing.settings_json = body.settings
        session.add(existing)

    await session.commit()
    return SettingsTelemetryResponse(ok=True)
