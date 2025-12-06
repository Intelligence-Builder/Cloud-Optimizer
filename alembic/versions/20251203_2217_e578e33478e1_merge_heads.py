"""Merge heads

Revision ID: e578e33478e1
Revises: b4591d8d37bd, 20251203_2148
Create Date: 2025-12-03 22:17:16.216119

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e578e33478e1"
down_revision: Union[str, None] = ("b4591d8d37bd", "20251203_2148")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass
