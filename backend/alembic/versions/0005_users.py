"""users: tabla app_user (auth + multi-tenant por organización)

Revision ID: 0005_users
Revises: 0004_quotes
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_users"
down_revision: Union[str, None] = "0004_quotes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_app_user"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
            name="fk_app_user_organization",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_app_user_email", "app_user", ["email"], unique=True)
    op.create_index(
        "ix_app_user_organization_id", "app_user", ["organization_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_app_user_organization_id", table_name="app_user")
    op.drop_index("ix_app_user_email", table_name="app_user")
    op.drop_table("app_user")
