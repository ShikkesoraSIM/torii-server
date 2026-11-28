"""add torii_settings_telemetry table for anonymous client settings analytics"""

import sqlalchemy as sa
from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "f183a9c7d214"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "torii_settings_telemetry",
        sa.Column("install_hash", sa.String(64), primary_key=True, nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("app_version", sa.String(48), nullable=True),
        sa.Column("stream", sa.String(24), nullable=True),
        sa.Column("platform", sa.String(32), nullable=True),
        sa.Column("cpu_arch", sa.String(16), nullable=True),
        sa.Column("ui_theme", sa.String(32), nullable=True),
        sa.Column("classic_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("nsfw_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("open_folders_skins", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("open_folders_songs", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("potato_mode", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("lightweight_interface", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("renderer", sa.String(32), nullable=True),
        sa.Column("audio_mode", sa.String(32), nullable=True),
        sa.Column("settings_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_torii_settings_telemetry_updated", "torii_settings_telemetry", ["updated_at"])
    op.create_index("ix_torii_settings_telemetry_stream_updated", "torii_settings_telemetry", ["stream", "updated_at"])
    op.create_index("ix_torii_settings_telemetry_theme", "torii_settings_telemetry", ["ui_theme", "updated_at"])


def downgrade():
    op.drop_index("ix_torii_settings_telemetry_theme", table_name="torii_settings_telemetry")
    op.drop_index("ix_torii_settings_telemetry_stream_updated", table_name="torii_settings_telemetry")
    op.drop_index("ix_torii_settings_telemetry_updated", table_name="torii_settings_telemetry")
    op.drop_table("torii_settings_telemetry")
