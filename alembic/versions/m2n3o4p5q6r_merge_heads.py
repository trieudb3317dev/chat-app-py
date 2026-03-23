"""merge heads (e5f6g7h8i, f1g2h3i4j5k)

Revision ID: m2n3o4p5q6r
Revises: e5f6g7h8i, f1g2h3i4j5k
Create Date: 2026-03-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'm2n3o4p5q6r'
down_revision = ('e5f6g7h8i', 'f1g2h3i4j5k')
branch_labels = None
depends_on = None


def upgrade():
    # merge migration: no schema changes, used to consolidate multiple heads
    pass


def downgrade():
    # no-op
    pass
