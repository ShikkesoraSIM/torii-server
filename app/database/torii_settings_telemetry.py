"""Anonymous aggregated Torii client settings telemetry.

Stores one latest settings snapshot per anonymous install hash (upsert on
``install_hash``) so admins can see real percentage breakdowns of active
installs (e.g. % using Classic UI, UI themes, Open Folders, Potato Mode,
NSFW toggle, renderers, audio modes) without storing PII, usernames,
file paths, or personal identifiers.
"""

from datetime import datetime

from app.utils import utcnow

from sqlalchemy import Boolean, Column, DateTime, Index, JSON, String
from sqlmodel import Field, SQLModel


class ToriiSettingsTelemetry(SQLModel, table=True):
    """Latest anonymous configuration snapshot per Torii client installation."""

    __tablename__: str = "torii_settings_telemetry"
    __table_args__ = (
        Index("ix_torii_settings_telemetry_updated", "updated_at"),
        Index("ix_torii_settings_telemetry_stream_updated", "stream", "updated_at"),
        Index("ix_torii_settings_telemetry_theme", "ui_theme", "updated_at"),
    )

    install_hash: str = Field(
        sa_column=Column(
            String(64),
            primary_key=True,
            nullable=False,
            comment="Salted SHA-256 of an anonymous client-generated install GUID. No user ID or PII.",
        ),
    )

    first_seen_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, nullable=False),
    )

    app_version: str | None = Field(default=None, sa_column=Column(String(48), nullable=True))
    stream: str | None = Field(default=None, sa_column=Column(String(24), nullable=True))
    platform: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))
    cpu_arch: str | None = Field(default=None, sa_column=Column(String(16), nullable=True))

    ui_theme: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))
    classic_enabled: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    nsfw_enabled: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    open_folders_skins: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    open_folders_songs: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    potato_mode: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    lightweight_interface: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    renderer: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))
    audio_mode: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))

    settings_json: dict | None = Field(
        default=None,
        sa_column=Column(
            JSON,
            nullable=True,
            comment="Bounded map of anonymous enum/bool/numeric configuration flags for dynamic aggregation.",
        ),
    )
