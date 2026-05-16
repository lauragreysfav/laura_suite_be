"""add torbox_downloads table

Revision ID: 20260516b
Revises: 16aff1fb1e4d
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260516b"
down_revision: Union[str, None] = "16aff1fb1e4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "torbox_downloads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("info_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("torbox_id", sa.Integer(), nullable=True),
        sa.Column("stash_scanned", sa.Boolean(), default=False),
        sa.Column("stash_identified", sa.Boolean(), default=False),
        sa.Column("stash_scene_id", sa.Integer(), nullable=True),
        sa.Column("stash_scene_name", sa.String(length=500), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("torbox_downloads")
