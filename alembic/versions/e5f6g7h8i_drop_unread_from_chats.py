"""drop unread from chats

Revision ID: e5f6g7h8i
Revises: d4e5f6g7h8i
Create Date: 2026-03-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i'
down_revision = 'd4e5f6g7h8i'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('chats')]
    if 'unread' in cols or 'un_read' in cols:
        # Prefer dropping the normalized name `unread`; also handle legacy `un_read`.
        try:
            if 'unread' in cols:
                op.drop_column('chats', 'unread')
            if 'un_read' in cols:
                op.drop_column('chats', 'un_read')
        except Exception:
            # Fall back to executing raw SQL which will be database-specific
            conn.execute("ALTER TABLE chats DROP COLUMN IF EXISTS unread;")
            conn.execute("ALTER TABLE chats DROP COLUMN IF EXISTS un_read;")


def downgrade():
    # recreate the column with a safe default so downgrade is non-destructive
    op.add_column('chats', sa.Column('unread', sa.Integer(), nullable=False, server_default='0'))
    # remove server_default to match model expectation (if desired) in future migrations
    with op.batch_alter_table('chats'):
        op.alter_column('unread', server_default=None)
