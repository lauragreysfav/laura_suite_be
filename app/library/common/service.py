import logging
from app.services.typesense_client import TypesenseClient
from app.library.common.typesense_schema import SCHEMAS

logger = logging.getLogger("laura.library.common.service")


def initialize_search() -> None:
    TypesenseClient().ensure_collections(SCHEMAS)


def upsert_entity(index: str, stashdb_id: str, data: dict):
    from app.library.common.repository import index_document
    index_document(index, stashdb_id, data)


def remove_entity(index: str, stashdb_id: str):
    from app.library.common.repository import delete_document
    delete_document(index, stashdb_id)
