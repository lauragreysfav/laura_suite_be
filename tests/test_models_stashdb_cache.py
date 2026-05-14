from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache, StandardSearchHistory


def test_performer_cache_has_new_fields():
    assert hasattr(StashDBPerformerCache, "gender")
    assert hasattr(StashDBPerformerCache, "birthdate")
    assert hasattr(StashDBPerformerCache, "urls")
    assert hasattr(StashDBPerformerCache, "raw_json")


def test_studio_cache_has_urls():
    assert hasattr(StashDBStudioCache, "urls")
    assert hasattr(StashDBStudioCache, "raw_json")


def test_scene_cache_exists():
    assert hasattr(StashDBSceneCache, "fingerprints")
    assert hasattr(StashDBSceneCache, "raw_json")
    assert hasattr(StashDBSceneCache, "performer_names")
    assert hasattr(StashDBSceneCache, "images")


def test_history_model():
    assert hasattr(StandardSearchHistory, "user_id")
    assert hasattr(StandardSearchHistory, "query")
    assert hasattr(StandardSearchHistory, "filters")
    assert hasattr(StandardSearchHistory, "result_count")
