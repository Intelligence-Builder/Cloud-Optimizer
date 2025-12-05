"""Add password reset columns to users.

Revision ID: 20251203_2220
Revises: e578e33478e1
Create Date: 2025-12-03 22:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251203_2220"
down_revision: str | None = "e578e33478e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add password reset columns to users table."""
    # Add password reset token hash column
    op.add_column(
        "users",
        sa.Column("password_reset_token_hash", sa.String(255), nullable=True),
    )

    # Add password reset expires_at column
    op.add_column(
        "users",
        sa.Column(
            "password_reset_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove password reset columns from users table."""
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
