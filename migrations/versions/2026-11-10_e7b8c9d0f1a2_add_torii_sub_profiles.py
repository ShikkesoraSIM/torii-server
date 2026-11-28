"""add torii_sub_profiles table

Revision ID: e7b8c9d0f1a2
Revises: 7b2d9e4f1a63
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b8c9d0f1a2"
down_revision: str | Sequence[str] | None = "7b2d9e4f1a63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "torii_sub_profiles"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _TABLE not in insp.get_table_names():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, primary_key=True),
            sa.Column("master_user_id", sa.BigInteger(), nullable=False),
            sa.Column("profile_user_id", sa.BigInteger(), nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("tag", sa.String(length=16), nullable=False),
            sa.Column("restriction_mode", sa.String(length=32), nullable=False, server_default="free"),
            sa.Column("required_mods", sa.Text(), nullable=False),
            sa.Column("allowed_mods", sa.Text(), nullable=False),
            sa.Column("disallowed_mods", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["master_user_id"], ["lazer_users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["profile_user_id"], ["lazer_users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("profile_user_id", name="uq_torii_sub_profile_user_id"),
        )
        op.create_index("ix_torii_sub_profiles_master_user_id", _TABLE, ["master_user_id"])
        op.create_index("ix_torii_sub_profiles_profile_user_id", _TABLE, ["profile_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _TABLE in insp.get_table_names():
        op.drop_table(_TABLE)
