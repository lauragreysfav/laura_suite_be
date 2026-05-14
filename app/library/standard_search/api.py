import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services import prowlarr
from app.services.prowlarr_search import stream_search, classify_xxx_type
from app.library.standard_search import service as std_search_service
from app.library.standard_search.schema import SuggestResult
from app.auth.dependencies import verify_token
from app.database import SessionLocal
from app.models import StandardSearchHistory

logger = logging.getLogger("laura.library.standard_search.api")
router = APIRouter(prefix="/prowlarr", tags=["standard_search"])


@router.websocket("/ws")
async def standard_search_ws(websocket: WebSocket):
    await websocket.accept()
    db = None
    history = None
    try:
        token = websocket.query_params.get("access_token") or ""
        if not token:
            await websocket.close(code=4401)
            return
        try:
            user = verify_token(token)
        except Exception:
            await websocket.close(code=4401)
            return

        data = await websocket.receive_json()
        query = data.get("query", "")
        categories = data.get("categories")
        indexer_ids = data.get("indexer_ids")
        xxx_type = data.get("xxx_type", "both")
        search_type = data.get("search_type", "search")

        db = SessionLocal()
        filters = {
            "categories": categories,
            "indexers": indexer_ids,
            "xxx_type": xxx_type,
        }
        history = StandardSearchHistory(
            user_id=user["sub"],
            query=query,
            filters=filters,
            status="running",
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        await websocket.send_json({"type": "status", "message": "Searching..."})

        processed = await stream_search(
            query=query,
            categories=categories,
            indexer_ids=indexer_ids,
            xxx_type=xxx_type,
            search_type=search_type,
        )

        await websocket.send_json({
            "type": "results",
            "results": processed,
            "total": len(processed),
        })

        if processed:
            hashes = [r.get("infoHash", "") for r in processed if r.get("infoHash")]
            if hashes:
                enriched = await std_search_service.enrich_by_hashes(hashes)
                for r in processed:
                    ih = r.get("infoHash", "").lower()
                    if ih in enriched:
                        await websocket.send_json({
                            "type": "enrichment",
                            "info_hash": ih,
                            "data": enriched[ih],
                        })

        history.status = "completed"
        history.result_count = len(processed)
        history.completed_at = datetime.now(timezone.utc)
        db.commit()

        await websocket.send_json({"type": "complete", "total": len(processed)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        if db and history:
            history.status = "error"
            history.error = str(e)
            history.completed_at = datetime.now(timezone.utc)
            db.commit()
        await websocket.send_json({"type": "error", "message": str(e)})
        logger.warning("ws_error", extra={"error": str(e)})
    finally:
        if db:
            db.close()
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/categories/tree")
def get_category_tree():
    try:
        return prowlarr.get_categories()
    except Exception as e:
        return {"error": str(e)}


@router.get("/indexers/mapped")
def get_indexers_mapped():
    try:
        indexers = prowlarr.list_indexers()
        result = []
        for idx in indexers:
            if isinstance(idx, dict):
                result.append({
                    "id": idx.get("id"),
                    "name": idx.get("name"),
                    "protocol": idx.get("protocol"),
                    "privacy": idx.get("privacy"),
                    "enabled": idx.get("enable", False),
                    "xxx_type": classify_xxx_type(idx.get("id", 0), idx.get("name", "")),
                    "categories": idx.get("capabilities", {}).get("categories", []),
                })
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/suggest", response_model=dict)
def suggest(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query("all", regex="^(performer|studio|scene|all)$"),
):
    try:
        results = std_search_service.suggest(q, search_type=type)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}
