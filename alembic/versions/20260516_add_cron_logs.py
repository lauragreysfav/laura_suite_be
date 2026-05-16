"""add cron_job_logs table

Revision ID: 20260516
Revises: 20260515
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260516"
down_revision: Union[str, None] = "20260515"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cron_job_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("checked_count", sa.Integer(), default=0),
        sa.Column("deleted_count", sa.Integer(), default=0),
        sa.Column("deleted_items", sa.JSON(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), default=0),
        sa.Column("ran_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("cron_job_logs")
