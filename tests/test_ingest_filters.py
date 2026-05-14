from scripts.initial_ingest import should_include_scene


def test_scene_year_filter():
    assert should_include_scene("2000-01-01") is True
    assert should_include_scene("1999-12-31") is False
