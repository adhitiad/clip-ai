import inspect

from backend.services.viral_predictor import predict_viral_score


def test_predict_viral_score_accepts_threshold_keyword():
    parameters = inspect.signature(predict_viral_score).parameters
    assert "threshold" in parameters
    assert parameters["threshold"].default is None


def test_app_exposes_expected_routers():
    from backend.main import app

    paths = set(app.openapi()["paths"])
    assert "/auth/google" in paths
    assert "/auth/token" not in paths
    assert "/auth/register" not in paths
    assert "/clips/generate-clips" in paths
    assert "/niche/analyze-and-queue" in paths
    assert "/tools/viral-score" in paths
    assert "/dashboard/overview" in paths


def test_worker_exports_render_task():
    from taskiq_aio_pika import AioPikaBroker

    from workers.worker import broker, process_all_clips_task

    assert isinstance(broker, AioPikaBroker)
    assert process_all_clips_task.task_name.endswith("process_all_clips_task")
