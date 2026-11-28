"""persist configured sub-profile mods"""

import sqlalchemy as sa
from alembic import op

revision = "f183a9c7d214"
down_revision = "e7b8c9d0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("torii_sub_profiles", sa.Column("mod_policy", sa.Text(), nullable=True))
    op.add_column("torii_sub_profiles", sa.Column("ruleset_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("torii_sub_profiles", sa.Column("creation_key", sa.String(36), nullable=True))
    op.create_unique_constraint("uq_sub_profile_creation_key", "torii_sub_profiles", ["creation_key"])


def downgrade():
    op.drop_constraint("uq_sub_profile_creation_key", "torii_sub_profiles", type_="unique")
    op.drop_column("torii_sub_profiles", "creation_key")
    op.drop_column("torii_sub_profiles", "ruleset_id")
    op.drop_column("torii_sub_profiles", "mod_policy")
