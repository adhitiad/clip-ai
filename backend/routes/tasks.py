"""Status task Taskiq (PostgreSQL + cache memori) untuk polling UI."""

from fastapi import APIRouter, Depends

from backend.core.auth import get_current_active_user
from backend.core.task_results import get_task_snapshot

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}")
def get_task_status(task_id: str, _user=Depends(get_current_active_user)):
    """Status task render: PENDING / PROGRESS / SUCCESS / FAILURE."""
    return get_task_snapshot(task_id)
