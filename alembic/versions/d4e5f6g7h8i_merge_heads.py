"""merge heads

Revision ID: d4e5f6g7h8i
Revises: b1c2d3e4f5a, c3d4e5f6a7b
Create Date: 2026-02-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i'
down_revision = ('b1c2d3e4f5a', 'c3d4e5f6a7b')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge (no-op) migration to combine multiple heads into a single head.
    pass


def downgrade():
    # downgrade would be ambiguous for merges; no-op
    pass
