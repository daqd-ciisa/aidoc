"""document.vendor + origin_url: metadata de fuentes aprobadas (doc_type=reference)

Revision ID: 0008_document_reference_source
Revises: 0007_document_doc_type
Create Date: 2026-06-17

Las fuentes aprobadas (QuickSpecs de HPE, guías validadas de Aruba, Microsoft 365
Learn…) se cargan como documentos con doc_type='reference'. Estas dos columnas
guardan la etiqueta de fabricante/tipo y la URL de origen cuando se dan de alta
por web. Nullables: los documentos existentes quedan con NULL.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_document_reference_source"
down_revision: Union[str, None] = "0007_document_doc_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document", sa.Column("vendor", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "document", sa.Column("origin_url", sa.String(length=1024), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("document", "origin_url")
    op.drop_column("document", "vendor")
