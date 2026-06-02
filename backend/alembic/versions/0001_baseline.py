"""baseline: tabla organization + tenant default

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_organization"),
        sa.UniqueConstraint("slug", name="uq_organization_slug"),
    )

    # Tenant por defecto (single-tenant hoy).
    op.execute(
        "INSERT INTO organization (id, slug, name, created_at, updated_at) "
        "VALUES ('00000000-0000-0000-0000-000000000000', 'default', 'Default', "
        "now(), now())"
    )


def downgrade() -> None:
    op.drop_table("organization")
