"""add is_verified column to user_admins

Revision ID: c3d4e5f6a7b
Revises: 0001_add_user_admin_columns
Create Date: 2026-02-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b'
down_revision = '0001_add_user_admin_columns'
branch_labels = None
depends_on = None


def upgrade():
    # idempotent SQL: add is_verified if missing
    op.execute("""
    ALTER TABLE user_admins
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE user_admins
    DROP COLUMN IF EXISTS is_verified;
    """)