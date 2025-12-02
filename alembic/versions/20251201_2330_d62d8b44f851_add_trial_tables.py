"""add_trial_tables

Revision ID: d62d8b44f851
Revises: 001
Create Date: 2025-12-01 23:30:05.015570

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d62d8b44f851"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create trials table
    op.create_table(
        "trials",
        sa.Column(
            "trial_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trial_id"),
    )
    op.create_index(op.f("ix_trials_user_id"), "trials", ["user_id"], unique=True)

    # Create trial_usage table
    op.create_table(
        "trial_usage",
        sa.Column(
            "usage_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("trial_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.String(length=50), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trial_id"], ["trials.trial_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usage_id"),
        sa.UniqueConstraint("trial_id", "dimension", name="uq_trial_usage_dimension"),
    )
    op.create_index(
        op.f("ix_trial_usage_trial_id"), "trial_usage", ["trial_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop trial_usage table
    op.drop_index(op.f("ix_trial_usage_trial_id"), table_name="trial_usage")
    op.drop_table("trial_usage")

    # Drop trials table
    op.drop_index(op.f("ix_trials_user_id"), table_name="trials")
    op.drop_table("trials")
