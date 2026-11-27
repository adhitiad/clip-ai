"""CLI render dipanggil worker RabbitMQ: payload JSON stdin → hasil JSON stdout."""

import json
import sys

from backend.core.env import load_env

load_env("workers")


def main() -> int:
    payload = json.loads(sys.stdin.read())

    from backend.core.telemetry import log_event, span, start_trace
    from backend.services.content_intelligence import (
        analyze_video,
        apply_brief_to_clips,
        sanitize_terms,
        score_clips,
    )
    from backend.services.render_pipeline import render_clips

    lang = payload.get("lang", "id")
    start_trace(payload.get("traceparent"), payload.get("request_id", ""))
    log_event("rabbitmq.job.start", request_id=payload.get("request_id", ""))

    clips = payload.get("clips") or []
    trend_terms = sanitize_terms(payload.get("trend_terms"))

    with span("content.video_analysis", video_url=payload["video_url"]):
        analyzed = analyze_video(payload["video_url"], payload.get("topic", ""), lang)
        if analyzed:
            clips = analyzed

    with span("content.plan_merge", clips=len(clips), trends=len(trend_terms)):
        clips = apply_brief_to_clips(clips, payload.get("brief"), lang, trend_terms)

    with span("content.viral_score", clips=len(clips)):
        clips = score_clips(clips, payload.get("viral_threshold"))

    with span("rabbitmq.render", clips=len(clips)):
        result = render_clips(payload["video_url"], clips, lang)

    log_event("rabbitmq.job.done", cached=result.get("cached", False))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
