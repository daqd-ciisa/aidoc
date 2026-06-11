"""document.doc_type: distingue documentos normales de catálogos de referencia

Revision ID: 0007_document_doc_type
Revises: 0006_default_tenant_id
Create Date: 2026-06-11

Los catálogos (catálogo de servicios, tarifarios) se inyectan siempre como fuente
de números de parte/precios al generar cotizaciones y se excluyen de la búsqueda
de precedentes. Los documentos existentes quedan como 'document'.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_document_doc_type"
down_revision: Union[str, None] = "0006_default_tenant_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document",
        sa.Column(
            "doc_type",
            sa.String(length=16),
            nullable=False,
            server_default="document",
        ),
    )


def downgrade() -> None:
    op.drop_column("document", "doc_type")
