"""add user_admins columns

Revision ID: 0001_add_user_admin_columns
Revises: 
Create Date: 2026-02-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_user_admin_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
        # Add columns using IF NOT EXISTS to avoid duplicate-column errors when migration
        # was partially applied or the schema already contains some columns.
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS role VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS full_name VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS address VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS phone_number VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS gender VARCHAR;
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now();
        """)
        op.execute("""
        ALTER TABLE user_admins
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT false;
        """)

        # Ensure existing rows have a role value and enforce NOT NULL/default
        op.execute("UPDATE user_admins SET role = 'admin' WHERE role IS NULL")
        # Use ALTER ... SET DEFAULT and SET NOT NULL safely
        op.execute("ALTER TABLE user_admins ALTER COLUMN role SET DEFAULT 'admin'")
        op.execute("ALTER TABLE user_admins ALTER COLUMN role SET NOT NULL")


def downgrade():
    op.drop_column('user_admins', 'is_active')
    op.drop_column('user_admins', 'created_at')
    op.drop_column('user_admins', 'gender')
    op.drop_column('user_admins', 'date_of_birth')
    op.drop_column('user_admins', 'phone_number')
    op.drop_column('user_admins', 'address')
    op.drop_column('user_admins', 'full_name')
    op.drop_column('user_admins', 'role')
