"""merge heads

Revision ID: 16aff1fb1e4d
Revises: 20260516, a793636843fc
Create Date: 2026-05-16 02:23:10.250774

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '16aff1fb1e4d'
down_revision: Union[str, None] = ('20260516', 'a793636843fc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
