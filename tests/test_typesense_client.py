from unittest.mock import MagicMock
from app.services.typesense_client import build_hash_filter, build_search_params


def test_build_hash_filter():
    assert build_hash_filter(["aaa", "bbb"]) == "fingerprints:=[aaa,bbb]"


def test_build_search_params():
    params = build_search_params("alice", ["name", "aliases"], per_page=5, filters="gender:=female")
    assert params["q"] == "alice"
    assert params["query_by"] == "name,aliases"
    assert params["per_page"] == 5
    assert params["filter_by"] == "gender:=female"
