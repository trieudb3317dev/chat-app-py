"""safely add avatar_url and is_verified to users table

Revision ID: f1g2h3i4j5k
Revises: d4e5f6g7h8i
Create Date: 2026-03-06 00:00:00.000000
"""

import contextlib
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1g2h3i4j5k"
down_revision = "d4e5f6g7h8i"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _has_column(inspector, table_name: str, col_name: str) -> bool:
        try:
            cols = [c.get("name") for c in inspector.get_columns(table_name)]
            return col_name in cols
        except Exception:
            return False

    # Add avatar_url if missing
    if not _has_column(insp, "users", "avatar_url"):
        op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))

    # also add avatar for user_admins table (table name is 'user_admins')
    if not _has_column(insp, "user_admins", "avatar_url"):
        op.add_column(
            "user_admins", sa.Column("avatar_url", sa.String(), nullable=True)
        )

    # Add is_verified if missing (default false)
    if not _has_column(insp, "users", "is_verified"):
        # server_default applied to existing rows
        op.add_column(
            "users",
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=True,
                server_default=sa.sql.expression.false(),
            ),
        )
        # set NOT NULL default if desired: leave nullable to avoid issues during migration


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _has_column(inspector, table_name: str, col_name: str) -> bool:
        try:
            cols = [c.get("name") for c in inspector.get_columns(table_name)]
            return col_name in cols
        except Exception:
            return False

    if _has_column(insp, "users", "is_verified"):
        with contextlib.suppress(Exception):
            op.drop_column("users", "is_verified")
            
    if _has_column(insp, "users", "avatar_url"):
        with contextlib.suppress(Exception):
            op.drop_column("users", "avatar_url")
            
            
    if _has_column(insp, "user_admins", "avatar_url"):
        with contextlib.suppress(Exception):
            op.drop_column("user_admins", "avatar_url")