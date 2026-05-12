from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import WatchHistory
import httpx
from app.config import settings

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.get("/{scene_id}")
def get_recommendations(scene_id: int, db: Session = Depends(get_db)):
    try:
        r = httpx.post(
            f"{settings.stash_url}/graphql",
            json={
                "query": """
                query FindScene($id: ID!) {
                  findScene(id: $id) {
                    performers { id name }
                    studio { id name }
                    tags { id name }
                  }
                }
                """,
                "variables": {"id": str(scene_id)},
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("data", {}).get("findScene", {})
        if not data:
            return {"recommendations": []}

        performer_ids = [p["id"] for p in data.get("performers", [])]
        studio_id = data.get("studio", {}).get("id")
        tag_ids = [t["id"] for t in data.get("tags", [])]

        watched = set()
        wh = db.query(WatchHistory).all()
        for w in wh:
            watched.add(w.scene_id)

        filters = []
        if performer_ids:
            filters.append({"performers": {"mod": "OR", "value": performer_ids}})
        if studio_id:
            filters.append({"studios": {"mod": "OR", "value": [studio_id]}})

        search_r = httpx.post(
            f"{settings.stash_url}/graphql",
            json={
                "query": """
                query FindScenes($filter: SceneFilterType) {
                  findScenes(filter: {per_page: 20}, scene_filter: $filter) {
                    scenes { id title date }
                  }
                }
                """,
                "variables": {"filter": {"AND": filters} if filters else None},
            },
            timeout=10,
        )
        search_r.raise_for_status()
        scenes = search_r.json().get("data", {}).get("findScenes", {}).get("scenes", [])

        recommendations = [s for s in scenes if int(s["id"]) != scene_id and int(s["id"]) not in watched]
        return {"recommendations": recommendations[:10]}

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/dashboard/popular")
def get_popular(db: Session = Depends(get_db)):
    popular = (
        db.query(WatchHistory)
        .order_by(WatchHistory.play_count.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "scene_id": w.scene_id,
            "play_count": w.play_count,
            "last_played_at": w.last_played_at,
        }
        for w in popular
    ]
