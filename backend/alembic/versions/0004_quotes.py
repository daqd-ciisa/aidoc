"""quotes: tabla quote

Revision ID: 0004_quotes
Revises: 0003_chat
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_quotes"
down_revision: Union[str, None] = "0003_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quote",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_quote"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_session.id"],
            name="fk_quote_session_id_chat_session",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_quote_tenant_id", "quote", ["tenant_id"])
    op.create_index("ix_quote_session_id", "quote", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_session_id", table_name="quote")
    op.drop_index("ix_quote_tenant_id", table_name="quote")
    op.drop_table("quote")
