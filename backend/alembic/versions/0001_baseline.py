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

    # Tenant por defecto. El id ES el string 'default' a propósito: ese es el
    # tenant_id que usan TenantMixin (default) y config.DEFAULT_TENANT_ID, así el
    # tenant por defecto referencia una fila real. (Las DBs que sembraron el UUID
    # antiguo '00000000-...' se reconcilian en la migración 0006.)
    op.execute(
        "INSERT INTO organization (id, slug, name, created_at, updated_at) "
        "VALUES ('default', 'default', 'Default', now(), now())"
    )


def downgrade() -> None:
    op.drop_table("organization")
