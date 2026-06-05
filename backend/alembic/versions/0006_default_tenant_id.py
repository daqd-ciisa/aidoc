"""default tenant: alinea el id de la organización por defecto con el tenant 'default'

Revision ID: 0006_default_tenant_id
Revises: 0005_users
Create Date: 2026-06-04

La baseline (0001) sembró originalmente la organización por defecto con un UUID
('00000000-0000-0000-0000-000000000000'), pero todo el resto del sistema usa el
string 'default' como tenant_id (``TenantMixin`` default, ``config.DEFAULT_TENANT_ID``
y los datos del modo single-tenant previo). Eso dejaba el tenant 'default' apuntando
a una organización inexistente.

Esta migración reconcilia el id de esa organización a 'default' en las DBs que ya
sembraron el UUID antiguo. En instalaciones nuevas (donde la baseline ya siembra
'default') es un no-op. Como ``app_user.organization_id`` referencia
``organization.id`` sin ON UPDATE CASCADE, se suelta y recrea la FK para reescribir
el id.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_default_tenant_id"
down_revision: Union[str, None] = "0005_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_ID = "00000000-0000-0000-0000-000000000000"
_DEFAULT_ID = "default"
_FK = "fk_app_user_organization"


def _rename_default_org(bind, *, src: str, dst: str) -> None:
    """Reescribe el id de la org ``src`` a ``dst`` (y repunta sus usuarios)."""
    exists = bind.execute(
        sa.text("SELECT 1 FROM organization WHERE id = :src"), {"src": src}
    ).first()
    if exists is None:
        return  # nada que reconciliar
    op.drop_constraint(_FK, "app_user", type_="foreignkey")
    bind.execute(
        sa.text("UPDATE organization SET id = :dst WHERE id = :src"),
        {"dst": dst, "src": src},
    )
    bind.execute(
        sa.text(
            "UPDATE app_user SET organization_id = :dst WHERE organization_id = :src"
        ),
        {"dst": dst, "src": src},
    )
    op.create_foreign_key(
        _FK, "app_user", "organization", ["organization_id"], ["id"], ondelete="CASCADE"
    )


def upgrade() -> None:
    _rename_default_org(op.get_bind(), src=_LEGACY_ID, dst=_DEFAULT_ID)


def downgrade() -> None:
    _rename_default_org(op.get_bind(), src=_DEFAULT_ID, dst=_LEGACY_ID)
