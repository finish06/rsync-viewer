"""add media_items.removed_at and repair phantom deletion rows

Revision ID: c4d5e6f7a8b9
Revises: af991c7168e1
Create Date: 2026-08-29 15:10:00.000000

specs/insight-ui.md AC-029, AC-030.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.media_repair import repair_phantom_media

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "af991c7168e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_items", sa.Column("removed_at", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_media_items_removed_at"), "media_items", ["removed_at"], unique=False
    )
    repair_phantom_media(op.get_bind())


def downgrade() -> None:
    op.drop_index(op.f("ix_media_items_removed_at"), table_name="media_items")
    op.drop_column("media_items", "removed_at")
