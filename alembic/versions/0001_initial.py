"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline: semua model terdaftar di Base.metadata (via _import_models).
    # create_all idempoten per tabel, aman untuk DB yang sudah punya sebagian tabel.
    from backend.utils.db import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    # Tidak menghapus tabel secara otomatis: data produksi/lokal harus aman.
    # Gunakan SQL manual bila memang ingin rollback penuh.
    pass
