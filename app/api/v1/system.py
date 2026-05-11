from fastapi import APIRouter
from app.services import torbox, stash

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_status():
    result = {"torbox": {"status": "unknown"}, "stash": {"status": "unknown"}, "webdav": {"status": "unknown"}}

    try:
        user = torbox.get_user_info()
        plan = user.get("data", {}).get("plan", 0)
        result["torbox"] = {"status": "ok", "plan": plan}
    except Exception as e:
        result["torbox"] = {"status": "error", "detail": str(e)}

    try:
        sys = stash.status()
        data = sys.get("data", {}).get("systemStatus", {})
        result["stash"] = {"status": "ok", "db": data.get("databasePath"), "schema": data.get("databaseSchema")}
    except Exception as e:
        result["stash"] = {"status": "error", "detail": str(e)}

    try:
        ok = torbox.refresh_webdav()
        result["webdav"] = {"status": "ok" if ok else "error"}
    except Exception as e:
        result["webdav"] = {"status": "error", "detail": str(e)}

    overall = all(v["status"] == "ok" for v in result.values())
    degraded = "degraded" if not overall else "ok"
    return {"status": degraded, "services": result}
