"""add constraints and timestamps to aws accounts

Revision ID: 20251203_2148
Revises: 8b2566889924
Create Date: 2025-12-03 21:48:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251203_2148"
down_revision = "8b2566889924"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aws_accounts",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint(
        "uq_aws_account_user_account",
        "aws_accounts",
        ["user_id", "aws_account_id"],
    )
    op.create_index(
        "ix_aws_accounts_status",
        "aws_accounts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_aws_accounts_status", table_name="aws_accounts")
    op.drop_constraint(
        "uq_aws_account_user_account",
        "aws_accounts",
        type_="unique",
    )
    op.drop_column("aws_accounts", "updated_at")
