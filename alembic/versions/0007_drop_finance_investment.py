"""hapus modul finance & investment (project pribadi tanpa pembukuan uang)

Revision ID: 0007_drop_finance_investment
Revises: 0006_task_results_attempts
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_drop_finance_investment"
down_revision = "0006_task_results_attempts"
branch_labels = None
depends_on = None

TABLES = ("finance_transactions", "investor_shares", "app_valuations")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for name in TABLES:
        if name in tables:
            op.drop_table(name)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    for column in ("stripe_customer_id", "subscription_status"):
        if column in user_columns:
            op.drop_column("users", column)


def downgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column(
        "users", sa.Column("subscription_status", sa.String(), default="inactive")
    )

    op.create_table(
        "app_valuations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("total_valuation", sa.Float(), default=500000000.0),
        sa.Column("founder_share_pct", sa.Float(), default=53.0),
        sa.Column("available_share_pct", sa.Float(), default=47.0),
        sa.Column("currency", sa.String(), default="IDR"),
    )
    op.create_table(
        "investor_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("invested_amount", sa.Float(), nullable=False),
        sa.Column("share_pct", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
