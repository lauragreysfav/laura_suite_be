"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_config",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("host", sa.String(255), default="smtp.gmail.com"),
        sa.Column("port", sa.Integer(), default=587),
        sa.Column("user", sa.String(255), default=""),
        sa.Column("password", sa.String(255), default=""),
        sa.Column("from_addr", sa.String(255), default=""),
        sa.Column("enabled", sa.Boolean(), default=False),
        sa.Column("notify_on_job_complete", sa.Boolean(), default=True),
        sa.Column("notify_on_tracker_find", sa.Boolean(), default=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_table(
        "search_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("type", sa.String(50), default="general"),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("progress", sa.Integer(), default=0),
        sa.Column("result_count", sa.Integer(), default=0),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(255), unique=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_table(
        "trackers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("query", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_table(
        "watch_history",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("scene_id", sa.Integer(), nullable=False),
        sa.Column("resume_time", sa.Float(), default=0.0),
        sa.Column("play_count", sa.Integer(), default=0),
        sa.Column("play_duration", sa.Float(), default=0.0),
        sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tracker_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tracker_id", sa.Integer(), sa.ForeignKey("trackers.id"), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "tracked_releases",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tracker_id", sa.Integer(), sa.ForeignKey("trackers.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("info_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("magnet", sa.Text(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("quality", sa.String(50), nullable=True),
        sa.Column("seeders", sa.Integer(), default=0),
        sa.Column("leechers", sa.Integer(), default=0),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "search_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("search_jobs.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("info_hash", sa.String(64), nullable=False),
        sa.Column("magnet", sa.Text(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("indexer", sa.String(255), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("quality", sa.String(50), nullable=True),
        sa.Column("seeders", sa.Integer(), default=0),
        sa.Column("leechers", sa.Integer(), default=0),
        sa.Column("scene_id", sa.Integer(), nullable=True),
        sa.Column("relevance", sa.Float(), default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("search_results")
    op.drop_table("tracked_releases")
    op.drop_table("tracker_jobs")
    op.drop_table("watch_history")
    op.drop_table("trackers")
    op.drop_table("settings")
    op.drop_table("search_jobs")
    op.drop_table("email_config")
