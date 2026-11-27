"""task results: status + progress task Taskiq

Revision ID: 0005_task_results
Revises: 0004_table_search_indexes
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_task_results"
down_revision = "0004_table_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("task_results"):
        op.create_table(
            "task_results",
            sa.Column("task_id", sa.String(length=64), primary_key=True),
            sa.Column("status", sa.String(length=16), nullable=False, default="PENDING"),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("progress_current", sa.Integer(), nullable=False, default=0),
            sa.Column("progress_total", sa.Integer(), nullable=False, default=0),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    existing = {index["name"] for index in inspector.get_indexes("task_results")}
    if "ix_task_results_status" not in existing:
        op.create_index("ix_task_results_status", "task_results", ["status"])


def downgrade() -> None:
    op.drop_index("ix_task_results_status", table_name="task_results")
    op.drop_table("task_results")
