"""chat: tablas chat_session y chat_message

Revision ID: 0003_chat
Revises: 0002_documents
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_chat"
down_revision: Union[str, None] = "0002_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_session",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_chat_session"),
    )
    op.create_index("ix_chat_session_tenant_id", "chat_session", ["tenant_id"])

    op.create_table(
        "chat_message",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_chat_message"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_session.id"],
            name="fk_chat_message_session_id_chat_session",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_chat_message_tenant_id", "chat_message", ["tenant_id"])
    op.create_index("ix_chat_message_session_id", "chat_message", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_message_session_id", table_name="chat_message")
    op.drop_index("ix_chat_message_tenant_id", table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_index("ix_chat_session_tenant_id", table_name="chat_session")
    op.drop_table("chat_session")
