"""approved_url: URLs aprobadas consultadas en vivo en la validación

Revision ID: 0009_approved_url
Revises: 0008_document_reference_source
Create Date: 2026-06-17

Lista de URLs de fuentes aprobadas (HPE QuickSpecs, Microsoft 365 Learn…) por
tenant. El pase de validación las descarga EN VIVO para contrastar las
afirmaciones técnicas de las propuestas (a diferencia de los documentos
'reference', que se indexan una vez).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_approved_url"
down_revision: Union[str, None] = "0008_document_reference_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approved_url",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approved_url_tenant_id", "approved_url", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_approved_url_tenant_id", table_name="approved_url")
    op.drop_table("approved_url")
