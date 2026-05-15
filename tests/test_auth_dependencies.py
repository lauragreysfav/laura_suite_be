from app.auth import dependencies as deps


def test_verify_token_supports_es256_via_jwks(monkeypatch):
    token = "header.payload.signature"

    class _Key:
        key = "public-es256-key"

    class _FakeJwksClient:
        def get_signing_key_from_jwt(self, value: str):
            assert value == token
            return _Key()

    monkeypatch.setattr(deps, "_jwks_client", lambda: _FakeJwksClient(), raising=False)
    monkeypatch.setattr(deps.jwt, "get_unverified_header", lambda value: {"alg": "ES256"})

    def _decode(value, key, algorithms, audience, options=None):
        assert value == token
        assert key == "public-es256-key"
        assert algorithms == ["ES256"]
        assert audience == "authenticated"
        assert options == {"verify_iat": False}
        return {"sub": "user-1", "aud": "authenticated"}

    monkeypatch.setattr(deps.jwt, "decode", _decode)

    payload = deps.verify_token(token)
    assert payload["sub"] == "user-1"
