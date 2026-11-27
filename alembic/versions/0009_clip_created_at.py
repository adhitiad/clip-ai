"""clip_created_at — timestamp nyata untuk statistik 7 hari

Revision ID: 0009_clip_created_at
Revises: 0008_performance_feedback
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_clip_created_at"
down_revision = "0008_performance_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("clips")}
    if "created_at" not in columns:
        op.add_column(
            "clips",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    op.drop_column("clips", "created_at")
