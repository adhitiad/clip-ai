"""task results: kolom attempts untuk retry Taskiq

Revision ID: 0006_task_results_attempts
Revises: 0005_task_results
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_task_results_attempts"
down_revision = "0005_task_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("task_results")}
    if "attempts" not in columns:
        op.add_column(
            "task_results",
            sa.Column("attempts", sa.Integer(), nullable=False, default=0),
        )


def downgrade() -> None:
    op.drop_column("task_results", "attempts")
