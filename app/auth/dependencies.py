from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError
import jwt

from app.config import settings

security = HTTPBearer()


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required for JWKS verification")
    base = settings.supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json")


def _decode_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    algorithm = str(header.get("alg", "")).upper()
 
    if algorithm == "HS256":
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_iat": False},
        )
 
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[algorithm],
        audience="authenticated",
        options={"verify_iat": False},
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        return _decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def verify_token(token: str) -> dict:
    try:
        return _decode_token(token)
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except InvalidTokenError:
        raise Exception("Invalid token")
    except Exception:
        raise Exception("Invalid token")
