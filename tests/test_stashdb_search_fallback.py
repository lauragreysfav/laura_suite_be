from app.api.v1 import stashdb_search


def test_resolve_entity_return_order():
    stashdb_search._try_pg = lambda *a, **k: None
    stashdb_search._try_typesense = lambda *a, **k: None
    stashdb_search._try_live = lambda *a, **k: {"id": "x"}
    res = stashdb_search._resolve_entity("scene", "x", None)
    assert res["id"] == "x"
