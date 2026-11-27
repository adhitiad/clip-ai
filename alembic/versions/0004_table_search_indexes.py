"""table search indexes

Revision ID: 0004_table_search_indexes
Revises: 0003_personal
Create Date: 2026-11-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_table_search_indexes"
down_revision = "0003_personal"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_clips_title_en", "clips", ("title_en",)),
    ("ix_clips_topic", "clips", ("topic",)),
    ("ix_clips_score", "clips", ("score",)),
    ("ix_finance_category", "finance_transactions", ("category",)),
    ("ix_finance_type", "finance_transactions", ("type",)),
    ("ix_finance_created_at", "finance_transactions", ("created_at",)),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for name, table, columns in INDEXES:
        if table not in tables:
            continue
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, list(columns))


def downgrade() -> None:
    for name, table, columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
