"""add api_keys active/prefix index

Revision ID: b7c2d9e1f3a4
Revises: a3f1b2c4d5e6
Create Date: 2026-08-27 22:45:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c2d9e1f3a4"
down_revision: Union[str, Sequence[str], None] = "a3f1b2c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_api_keys_active_prefix",
        "api_keys",
        ["is_active", "key_prefix"],
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_active_prefix", table_name="api_keys")
