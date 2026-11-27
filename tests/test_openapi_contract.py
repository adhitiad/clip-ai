"""T-13: kontrak OpenAPI terkunci (docs mengikuti kode)."""

from backend.main import app

EXPECTED_PATHS = {
    "/auth/google",
    "/auth/me",
    "/agent/shorts",
    "/clips/generate-clips",
    "/clips/feedback",
    "/tasks/{task_id}",
    "/tools/dub",
    "/tools/viral-score",
    "/tools/model-status",
    "/tools/feedback",
    "/youtube/search",
    "/youtube/scheduler/status",
    "/youtube/scheduler/collect",
}

FORBIDDEN_FRAGMENTS = (
    "/auth/token",
    "/auth/register",
    "/auth/bootstrap-owner",
    "/auth/set-role",
    "/billing",
    "/dashboard/owner",
    "godsmode",
)


def test_openapi_paths_match_personal_scope():
    paths = set(app.openapi()["paths"])
    assert EXPECTED_PATHS <= paths
    for fragment in FORBIDDEN_FRAGMENTS:
        assert not any(fragment in path for path in paths), fragment


def test_dub_schema_has_script_text_and_no_password():
    schema = app.openapi()["components"]["schemas"]
    dub = schema["DubRequest"]["properties"]
    assert "script_text" in dub
    assert "password" not in dub
    assert "hashed_password" not in str(schema).lower()
