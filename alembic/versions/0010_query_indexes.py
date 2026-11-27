"""query indexes: task_results(status, updated_at), performance_feedback(created_at), clips(created_at)

Revision ID: 0010_query_indexes
Revises: 0009_clip_created_at
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_query_indexes"
down_revision = "0009_clip_created_at"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_task_results_status_updated_at", "task_results", ("status", "updated_at")),
    ("ix_performance_feedback_created_at", "performance_feedback", ("created_at",)),
    ("ix_clips_created_at", "clips", ("created_at",)),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table, columns in INDEXES:
        if not inspector.has_table(table):
            continue
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, list(columns))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table, _columns in reversed(INDEXES):
        if not inspector.has_table(table):
            continue
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name in existing:
            op.drop_index(name, table_name=table)
