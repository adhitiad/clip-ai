"""Guard: semua model harus terdaftar di metadata sebelum create_all."""

from backend.utils.db import Base, _import_models


def test_all_models_registered_in_metadata():
    _import_models()
    expected = {
        "users",
        "clips",
        "owner_settings",
        "user_settings",
        "task_results",
    }
    assert expected <= set(Base.metadata.tables)
