"""Project pribadi: tidak ada role, plan, atau kredit.

Satu-satunya dependency akses adalah login Google yang sudah terverifikasi.
Fungsi-fungsi lama (require_role/require_plan/check_credits/consume/refund)
sengaja dihapus — jangan menambahkannya kembali.
"""

from fastapi import Depends

from backend.core.auth import get_current_active_user
from backend.models.user import User


async def require_owner(current_user: User = Depends(get_current_active_user)) -> User:
    """Semua user yang login adalah pemilik (daftar putih OWNER_EMAILS)."""
    return current_user
