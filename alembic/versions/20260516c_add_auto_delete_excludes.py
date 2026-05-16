"""add auto_delete_excludes table

Revision ID: 20260516c
Revises: 20260516b
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260516c"
down_revision: Union[str, None] = "3f39ac11a6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auto_delete_excludes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("info_hash", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("auto_delete_excludes")
