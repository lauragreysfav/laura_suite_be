from app.services.magnet import build_magnet

def test_build_magnet():
    m = build_magnet("ABC123", "Test Title")
    assert m.startswith("magnet:?xt=urn:btih:ABC123")
    assert "dn=Test%20Title" in m

def test_build_magnet_no_title():
    m = build_magnet("ABC123")
    assert m == "magnet:?xt=urn:btih:ABC123"
