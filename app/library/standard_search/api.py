import logging
import traceback
import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.auth.dependencies import verify_token, get_current_user
from app.database import SessionLocal
from app.models import StandardSearchHistory
from app.services.prowlarr_search import stream_search, classify_xxx_type, dedup_results, rank_results
from app.services import prowlarr
from app.library.standard_search import service as std_search_service

logger = logging.getLogger("laura.library.standard_search.api")
router = APIRouter(prefix="/prowlarr", tags=["standard_search"])


@router.websocket("/ws")
async def standard_search_ws(websocket: WebSocket):
    await websocket.accept(subprotocol="access_token")
    
    # Now check for token after accepting
    raw_protocols = websocket.headers.get("Sec-WebSocket-Protocol", "")
    protocols = [p.strip() for p in raw_protocols.split(",") if p.strip()]
    
    token = None
    if "access_token" in protocols:
        idx = protocols.index("access_token")
        if idx + 1 < len(protocols):
            token = protocols[idx + 1]
    
    if not token:
        token = websocket.query_params.get("access_token")

    if not token:
        logger.warning("ws_auth_failed: no token found")
        await websocket.send_json({"type": "error", "message": "Authentication required"})
        await websocket.close(code=4401)
        return

    try:
        user = verify_token(token)
        logger.info(f"ws_auth_success: user={user.get('sub')}")
    except Exception as e:
        logger.warning(f"ws_auth_failed: token verify error: {str(e)}")
        await websocket.send_json({"type": "error", "message": f"Auth error: {str(e)}"})
        await websocket.close(code=4401)
        return

    db = None
    history = None
    try:
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
            "search_type": search_type,
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
        await websocket.send_json({"type": "log", "message": f"Query: {query} (type: {search_type})"})
        await websocket.send_json({"type": "log", "message": "Connecting to Prowlarr indexers..."})

        try:
            # v0.2.8 - Live Console Stats
            raw_results = await asyncio.to_thread(
                prowlarr.search,
                query=query,
                categories=categories,
                indexer_ids=indexer_ids,
                search_type=search_type,
            )
            
            if not raw_results:
                await websocket.send_json({"type": "log", "message": "No results found from indexers."})
                processed = []
            else:
                raw_count = len(raw_results)
                await websocket.send_json({"type": "log", "message": f"Found {raw_count} raw torrents across trackers."})
                
                processed = dedup_results(raw_results)
                dedup_count = len(processed)
                dupes_removed = raw_count - dedup_count
                
                if dupes_removed > 0:
                    await websocket.send_json({"type": "log", "message": f"Deduplication complete: Merged {dupes_removed} duplicates into {dedup_count} unique swarms."})
                
                # Filter by XXX type if needed
                if categories and any(6000 <= c < 7000 for c in (categories or [])):
                    if xxx_type != "both":
                        processed = [
                            r for r in processed
                            if classify_xxx_type(r.get("indexerId", 0), r.get("indexer", "")) == xxx_type
                        ]
                        await websocket.send_json({"type": "log", "message": f"Filtered results for {xxx_type.upper()} indexers only: {len(processed)} remaining."})

                # Reranking
                processed = rank_results(processed)
                await websocket.send_json({"type": "log", "message": "Results re-ranked by health and quality."})
        
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text
            except Exception:
                body = str(e)
            message = "Prowlarr search failed"
            if e.response.status_code == 400:
                body_lower = body.lower()
                if "unavailable" in body_lower:
                    message = "Selected indexers are unavailable"
                elif "query string exceeds" in body_lower or "too long" in body_lower:
                    message = "Search too broad — try fewer categories or indexers"
                else:
                    message = body[:200] if body else message
            history.status = "error"
            history.error = message
            history.completed_at = datetime.now(timezone.utc)
            db.commit()
            await websocket.send_json({"type": "error", "message": message})
            return

        await websocket.send_json({
            "type": "results",
            "results": processed,
            "total": len(processed),
        })

        if processed:
            # Enrichment background task (v0.2.7)
            
            async def background_enrich(all_items):
                hashes = [r.get("infoHash", "") for r in all_items if r.get("infoHash")]
                if not hashes:
                    return
                
                # Enrich in chunks of 50 to keep the WebSocket flowing
                CHUNK_SIZE = 50
                for i in range(0, len(hashes), CHUNK_SIZE):
                    chunk = hashes[i:i + CHUNK_SIZE]
                    try:
                        enriched = await std_search_service.enrich_by_hashes(chunk)
                        for ih, data in enriched.items():
                            # Map standard Scene object to the simplified 'enriched' UI structure
                            ui_data = {
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "images": [data.get("paths", {}).get("screenshot")] if data.get("paths", {}).get("screenshot") else [],
                                "studio": data.get("studio", {}).get("name") if data.get("studio") else None,
                                "performers": [p.get("name") for p in data.get("performers", []) if p.get("name")],
                            }
                            
                            try:
                                # v0.2.9 - Console log for enrichment
                                if ui_data["title"]:
                                    await websocket.send_json({
                                        "type": "log", 
                                        "message": f"✨ Enriched: {ui_data['title']} ({ui_data['studio'] or 'Unknown Studio'})"
                                    })

                                await websocket.send_json({
                                    "type": "enrichment",
                                    "info_hash": ih.lower(),
                                    "data": ui_data,
                                })
                            except Exception:
                                break # Websocket might be closed
                    except Exception as e:
                        logger.warning(f"background_enrich_chunk_failed: {str(e)}")
                        continue
                
                # Final update for database history
                try:
                    # Refresh from DB to avoid session issues in background task if needed, 
                    # but here we just need to update the history record
                    pass 
                except: pass

            asyncio.create_task(background_enrich(processed))

        history.status = "completed"
        history.results = processed
        history.result_count = len(processed)
        history.completed_at = datetime.now(timezone.utc)
        db.commit()

        await websocket.send_json({"type": "complete", "total": len(processed)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        tb = traceback.format_exc()
        if db and history:
            history.status = "error"
            history.error = f"{str(e)}\n{tb}"
            history.completed_at = datetime.now(timezone.utc)
            db.commit()
        await websocket.send_json({"type": "error", "message": str(e)})
        logger.warning("ws_error", extra={"error": str(e), "traceback": tb})
    finally:
        if db:
            db.close()
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/categories/tree")
def get_category_tree(user: dict = Depends(get_current_user)):
    try:
        return prowlarr.get_categories()
    except Exception as e:
        return {"error": str(e)}


@router.get("/indexers/mapped")
def get_indexers_mapped(user: dict = Depends(get_current_user)):
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
async def suggest(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query("all", regex="^(performer|studio|scene|all)$"),
    user: dict = Depends(get_current_user)
):
    try:
        results = await std_search_service.suggest(q, search_type=type)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}
