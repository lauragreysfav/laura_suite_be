from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services import stashdb_public
from app.services.prowlarr_search import stream_search, classify_xxx_type
from app.services import prowlarr

router = APIRouter(prefix="/prowlarr", tags=["prowlarr_search"])


@router.websocket("/ws")
async def standard_search_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        categories = data.get("categories")
        indexer_ids = data.get("indexer_ids")
        xxx_type = data.get("xxx_type", "both")
        search_type = data.get("search_type", "search")

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
                enriched = await stashdb_public.enrich_by_hashes(hashes)
                for r in processed:
                    ih = r.get("infoHash", "").lower()
                    if ih in enriched:
                        await websocket.send_json({
                            "type": "enrichment",
                            "info_hash": ih,
                            "data": enriched[ih],
                        })

        await websocket.send_json({"type": "complete", "total": len(processed)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/categories/tree")
def get_category_tree():
    try:
        return prowlarr.get_default_categories()
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
