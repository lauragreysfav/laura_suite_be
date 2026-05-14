from scripts.ingest.savers import _scene_to_pg, _scene_to_ts


def test_scene_year_filter():
    assert _scene_to_pg({"release_date": "2000-01-01", "id": "s1", "performers": []}) is not None
    assert _scene_to_pg({"release_date": "1999-12-31", "id": "s2", "performers": []}) is None
    assert _scene_to_pg({"id": "s3", "performers": []}) is None


def test_scene_ts_filter():
    assert _scene_to_ts({"release_date": "2000-01-01", "id": "s1"}) is not None
    assert _scene_to_ts({"release_date": "1999-12-31", "id": "s2"}) is None
