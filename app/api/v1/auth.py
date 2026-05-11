from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.services.supabase import get_supabase
from app.auth.dependencies import get_current_user

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/register")
def register(req: RegisterRequest):
    supabase = get_supabase()
    try:
        res = supabase.auth.admin.create_user(
            email=req.email,
            password=req.password,
            email_confirm=True,
        )
        return {"id": res.user.id, "email": res.user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login")
def login(req: LoginRequest):
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "user": {"id": res.user.id, "email": res.user.email},
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"sub": user.get("sub"), "email": user.get("email")}
