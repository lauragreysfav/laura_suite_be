from unittest.mock import Mock, patch

from app.services.torbox import create_torrent_from_download_url


def test_create_torrent_from_download_url_uploads_file():
    file_response = Mock()
    file_response.content = b"torrent-bytes"
    file_response.raise_for_status.return_value = None

    torbox_response = Mock()
    torbox_response.raise_for_status.return_value = None
    torbox_response.json.return_value = {"success": True}

    with patch("app.services.torbox.httpx.get", return_value=file_response) as mock_get, \
         patch("app.services.torbox.httpx.post", return_value=torbox_response) as mock_post:
        data = create_torrent_from_download_url("https://example.com/path/file.torrent", seed=1, name="Sample")

    assert data == {"success": True}
    mock_get.assert_called_once()
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert "files" in kwargs
    assert kwargs["data"]["seed"] == "1"
    assert kwargs["data"]["name"] == "Sample"
