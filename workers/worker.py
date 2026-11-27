"""Taskiq worker — fallback render di samping antrean RabbitMQ utama."""

import asyncio

from taskiq import Context, TaskiqDepends

from backend.core.env import load_env

load_env("workers")

from backend.core.taskiq_config import broker  # noqa: E402


@broker.task
async def process_all_clips_task(
    video_url: str,
    clips_metadata: list,
    lang: str,
    request_id: str | None = None,
    traceparent: str | None = None,
    mix_sources: bool = False,
    context: Context = TaskiqDepends(),
) -> dict:
    """Render klip via Taskiq; hasil tersimpan di PostgreSQL + cache memori."""
    from backend.core.request_id import set_request_id
    from backend.core.task_results import record_attempt, set_progress_sync
    from backend.core.telemetry import log_event, span, start_trace
    from backend.services.render_pipeline import render_clips

    if request_id:
        set_request_id(request_id)
    start_trace(traceparent, request_id or "")
    task_id = context.message.task_id
    attempt = int(context.message.labels.get("_retries", 0)) + 1
    await asyncio.to_thread(record_attempt, task_id, attempt)

    def progress(current: int, total: int) -> None:
        set_progress_sync(task_id, current, total)

    with span(
        "taskiq.render",
        clips=len(clips_metadata),
        mix_sources=mix_sources,
        request_id=request_id,
    ):
        log_event("taskiq.task.start", video_url=video_url, lang=lang)
        result = await asyncio.to_thread(
            render_clips,
            video_url,
            clips_metadata,
            lang,
            progress=progress,
            mix=mix_sources,
        )
        log_event("taskiq.task.done", cached=result.get("cached", False))
        return result
