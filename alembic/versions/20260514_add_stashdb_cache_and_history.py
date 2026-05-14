"""add stashdb cache and history

Revision ID: 20260514
Revises: 1dcc21e11f9c
Create Date: 2026-05-14 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260514"
down_revision: Union[str, None] = "1dcc21e11f9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stashdb_cache_performers", sa.Column("gender", sa.String(length=50), nullable=True))
    op.add_column("stashdb_cache_performers", sa.Column("birthdate", sa.String(length=50), nullable=True))
    op.add_column("stashdb_cache_performers", sa.Column("urls", sa.JSON(), nullable=True))

    op.add_column("stashdb_cache_studios", sa.Column("urls", sa.JSON(), nullable=True))

    op.create_table(
        "stashdb_cache_scenes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stashdb_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=500)),
        sa.Column("details", sa.Text()),
        sa.Column("release_date", sa.String(length=20)),
        sa.Column("duration", sa.Integer()),
        sa.Column("studio_name", sa.String(length=255)),
        sa.Column("studio_id", sa.String(length=255)),
        sa.Column("performer_names", sa.JSON()),
        sa.Column("performer_ids", sa.JSON()),
        sa.Column("tags", sa.JSON()),
        sa.Column("fingerprints", sa.JSON()),
        sa.Column("images", sa.JSON()),
        sa.Column("raw_json", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "standard_search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("filters", sa.JSON()),
        sa.Column("result_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(length=50), server_default="running"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_standard_search_history_user_id", "standard_search_history", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_standard_search_history_user_id")
    op.drop_table("standard_search_history")
    op.drop_table("stashdb_cache_scenes")
    op.drop_column("stashdb_cache_studios", "urls")
    op.drop_column("stashdb_cache_performers", "urls")
    op.drop_column("stashdb_cache_performers", "birthdate")
    op.drop_column("stashdb_cache_performers", "gender")
