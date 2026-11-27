"""google auth column

Revision ID: 0002_google_auth
Revises: 0001_initial
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_google_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "google_sub" not in columns:
        op.add_column("users", sa.Column("google_sub", sa.String(), nullable=True))
    if "ix_users_google_sub" not in indexes:
        op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
