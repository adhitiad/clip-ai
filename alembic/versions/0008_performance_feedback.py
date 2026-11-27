"""performance_feedback — riwayat feedback untuk kalibrasi rule-based

Revision ID: 0008_performance_feedback
Revises: 0007_drop_finance_investment
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_performance_feedback"
down_revision = "0007_drop_finance_investment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("performance_feedback"):
        op.create_table(
            "performance_feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clip_id", sa.Integer(), nullable=False, index=True),
            sa.Column("actual_views", sa.Integer(), default=0),
            sa.Column("actual_likes", sa.Integer(), default=0),
            sa.Column("actual_shares", sa.Integer(), default=0),
            sa.Column("predicted_score", sa.Float(), default=0.0),
            sa.Column("real_score", sa.Float(), default=0.0),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    existing = {
        index["name"] for index in inspector.get_indexes("performance_feedback")
    }
    if "ix_performance_feedback_clip_id" not in existing:
        op.create_index(
            "ix_performance_feedback_clip_id", "performance_feedback", ["clip_id"]
        )


def downgrade() -> None:
    op.drop_table("performance_feedback")
