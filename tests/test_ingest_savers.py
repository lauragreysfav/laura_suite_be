from unittest.mock import MagicMock
from scripts.ingest.savers import batch_save_performers, batch_save_studios, batch_save_scenes


def test_batch_save_performers():
    session = MagicMock()
    ts = MagicMock()
    performers = [
        {"id": "p1", "name": "Alice", "gender": "female", "aliases": "", "images": [], "urls": [],
         "scene_count": 5, "birth_date": "1990-01-01"}
    ]
    saved = batch_save_performers(session, ts, performers, batch_size=10)
    assert saved == 1
    assert session.bulk_save_objects.called
    ts.bulk_upsert.assert_called_once()


def test_batch_save_performers_skips_male():
    session = MagicMock()
    ts = MagicMock()
    performers = [
        {"id": "p1", "name": "Bob", "gender": "male"}
    ]
    saved = batch_save_performers(session, ts, performers, batch_size=10)
    assert saved == 0
    session.bulk_save_objects.assert_not_called()


def test_batch_save_studios():
    session = MagicMock()
    ts = MagicMock()
    studios = [
        {"id": "st1", "name": "Studio A", "images": [], "scene_count": 10, "urls": []}
    ]
    saved = batch_save_studios(session, ts, studios)
    assert saved == 1
    session.bulk_save_objects.assert_called_once()
    ts.bulk_upsert.assert_called_once()


def test_batch_save_scenes():
    session = MagicMock()
    ts = MagicMock()
    scenes = [
        {"id": "s1", "title": "Scene 1", "release_date": "2020-01-01", "details": "",
         "duration": 3600, "images": [], "performers": [], "fingerprints": [],
         "tags": [], "studio": {"id": "st1", "name": "Studio A"}}
    ]
    saved = batch_save_scenes(session, ts, scenes)
    assert saved == 1
    session.bulk_save_objects.assert_called_once()
    ts.bulk_upsert.assert_called_once()


def test_batch_save_scenes_filters_old():
    session = MagicMock()
    ts = MagicMock()
    scenes = [
        {"id": "s1", "title": "Old", "release_date": "1999-01-01", "performers": [],
         "fingerprints": [], "tags": [], "studio": {}}
    ]
    saved = batch_save_scenes(session, ts, scenes)
    assert saved == 0
    session.bulk_save_objects.assert_not_called()
