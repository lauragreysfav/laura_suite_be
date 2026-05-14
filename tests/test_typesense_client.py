from unittest.mock import MagicMock, patch
from app.services.typesense_client import TypesenseClient, build_hash_filter, build_search_params


def test_build_hash_filter():
    assert build_hash_filter(["aaa", "bbb"]) == "fingerprints:=[aaa,bbb]"


def test_build_search_params():
    params = build_search_params("alice", ["name", "aliases"], per_page=5, filters="gender:=female")
    assert params["q"] == "alice"
    assert params["query_by"] == "name,aliases"
    assert params["per_page"] == 5
    assert params["filter_by"] == "gender:=female"


def test_client_init_parses_url():
    with patch("app.services.typesense_client.settings") as mock_settings:
        mock_settings.typesense_host = "http://typesense:8108"
        mock_settings.typesense_api_key = "test-key"
        mock_settings.typesense_timeout = 5
        with patch("app.services.typesense_client.typesense.Client") as mock_client:
            TypesenseClient()
            config = mock_client.call_args[0][0]
            node = config["nodes"][0]
            assert node["host"] == "typesense"
            assert node["port"] == 8108
            assert node["protocol"] == "http"
            assert config["api_key"] == "test-key"


def test_client_init_defaults():
    with patch("app.services.typesense_client.settings") as mock_settings:
        mock_settings.typesense_host = "https://ts.example.com:443"
        mock_settings.typesense_api_key = ""
        mock_settings.typesense_timeout = 10
        with patch("app.services.typesense_client.typesense.Client") as mock_client:
            TypesenseClient()
            config = mock_client.call_args[0][0]
            node = config["nodes"][0]
            assert node["host"] == "ts.example.com"
            assert node["port"] == 443
            assert node["protocol"] == "https"


def test_get_returns_none_on_miss():
    with patch("app.services.typesense_client.settings") as mock_settings:
        mock_settings.typesense_host = "http://typesense:8108"
        mock_settings.typesense_api_key = "test-key"
        mock_settings.typesense_timeout = 5
        with patch("app.services.typesense_client.typesense.Client") as mock_client:
            fake_coll = MagicMock()
            fake_coll.documents["nope"].retrieve.side_effect = __import__("typesense").exceptions.ObjectNotFound("")
            mock_client.return_value.collections.__getitem__.return_value = fake_coll
            client = TypesenseClient()
            assert client.get("stashdb_performers", "nope") is None


def test_search_by_hashes_returns_documents():
    with patch("app.services.typesense_client.settings") as mock_settings:
        mock_settings.typesense_host = "http://typesense:8108"
        mock_settings.typesense_api_key = "test-key"
        mock_settings.typesense_timeout = 5
        with patch("app.services.typesense_client.typesense.Client") as mock_client:
            fake_coll = MagicMock()
            fake_coll.documents.search.return_value = {
                "hits": [{"document": {"id": "x", "fingerprints": ["abc"]}}]
            }
            mock_client.return_value.collections.__getitem__.return_value = fake_coll
            client = TypesenseClient()
            result = client.search_by_hashes("stashdb_scenes", ["abc"])
            assert len(result) == 1
            assert result[0]["id"] == "x"
