"""add is_verified column to users

Revision ID: b1c2d3e4f5a
Revises: 0001_add_user_admin_columns
Create Date: 2026-02-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a'
down_revision = '0001_add_user_admin_columns'
branch_labels = None
depends_on = None


def upgrade():
    # idempotent raw SQL to add column if it doesn't exist
    op.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE users
    DROP COLUMN IF EXISTS is_verified;
    """)
