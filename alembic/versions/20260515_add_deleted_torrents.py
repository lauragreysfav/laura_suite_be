"""add deleted_torrents table

Revision ID: 20260515
Revises: 20260514
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260515"
down_revision: Union[str, None] = "20260514"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deleted_torrents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("info_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("magnet", sa.Text(), nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.String(length=50), default="auto"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("deleted_torrents")
