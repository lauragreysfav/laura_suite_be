from app.services.prowlarr_results import normalize_result


def test_normalize_direct_magnet():
    item = normalize_result({
        "title": "Example",
        "magnetUrl": "magnet:?xt=urn:btih:abc",
        "infoHash": "0123456789abcdef0123456789abcdef01234567",
    })
    assert item["magnetUrl"] == "magnet:?xt=urn:btih:abc"
    assert item["linkType"] == "direct"
    assert item["canSubmitToTorbox"] is True


def test_normalize_synthesizes_magnet_from_info_hash():
    item = normalize_result({
        "title": "Example Title",
        "infoHash": "0123456789abcdef0123456789abcdef01234567",
    })
    assert item["magnetUrl"].startswith("magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567")
    assert item["linkType"] == "synthesized"
    assert item["magnetSource"] == "synthesized"


def test_normalize_preserves_torrent_download_url():
    item = normalize_result({
        "title": "Example Title",
        "downloadUrl": "https://example.com/file.torrent",
    })
    assert item["magnetUrl"] == ""
    assert item["downloadUrl"] == "https://example.com/file.torrent"
    assert item["linkType"] == "torrent-file"
