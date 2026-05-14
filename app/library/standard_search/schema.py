from pydantic import BaseModel
from typing import Optional


class SuggestRequest(BaseModel):
    q: str
    type: str = "all"


class SuggestResult(BaseModel):
    id: str
    name: str
    type: str
    image_url: Optional[str] = None
    studio_name: Optional[str] = None


class EnrichmentData(BaseModel):
    title: Optional[str] = None
    images: list[str] = []
    performers: list[str] = []
    studio: Optional[str] = None


class WsSearchMessage(BaseModel):
    query: str
    categories: Optional[list[int]] = None
    indexer_ids: Optional[list[int]] = None
    xxx_type: str = "both"
    search_type: str = "search"


class BatchAddRequest(BaseModel):
    magnets: list[str]
    seed: int = 1
