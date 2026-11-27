"""personal project: drop role/plan/credits

Revision ID: 0003_personal
Revises: 0002_google_auth
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_personal"
down_revision = "0002_google_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    for column in ("credits", "used_credits", "role", "plan"):
        if column in columns:
            op.drop_column("users", column)
    for enum_name in ("userrole", "userplan"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")


def downgrade() -> None:
    op.add_column("users", sa.Column("plan", sa.String(), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(), nullable=True))
    op.add_column("users", sa.Column("used_credits", sa.Integer(), default=0))
    op.add_column("users", sa.Column("credits", sa.Integer(), default=3))
