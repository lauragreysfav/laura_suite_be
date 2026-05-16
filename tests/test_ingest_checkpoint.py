from unittest.mock import MagicMock
from scripts.ingest.checkpoint import Checkpoint
from app.models import IngestCheckpoint


def test_checkpoint_save_and_load():
    db = MagicMock()
    
    # Mock for initial load (not found)
    db.query.return_value.filter_by.return_value.first.return_value = None
    
    cp = Checkpoint(db, key="test")
    cp.load()
    cp.set("performers_page", 5)
    
    # Mock for save - it should find nothing and then create
    db.query.return_value.filter_by.return_value.first.return_value = None
    cp.save()
    
    # Verify add and commit
    db.add.assert_called_once()
    db.commit.assert_called()
    
    added_obj = db.add.call_args[0][0]
    assert isinstance(added_obj, IngestCheckpoint)
    assert added_obj.key == "test"
    assert added_obj.data["performers_page"] == 5

    # Mock for next load (found)
    db.query.return_value.filter_by.return_value.first.return_value = added_obj
    
    cp2 = Checkpoint(db, key="test")
    cp2.load()
    assert cp2.get("performers_page") == 5


def test_checkpoint_defaults():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    
    cp = Checkpoint(db)
    cp.load()
    assert cp.get("phase") == "performers"
    assert cp.get("seen_performer_ids") == []


def test_checkpoint_append():
    db = MagicMock()
    # Mock existing record
    mock_ckpt = IngestCheckpoint(key="test", data={"seen_studio_ids": ["s1"]})
    db.query.return_value.filter_by.return_value.first.return_value = mock_ckpt
    
    cp = Checkpoint(db, key="test")
    cp.load()
    cp.append("seen_studio_ids", "s2")
    cp.append("seen_studio_ids", "s1")  # duplicate
    
    cp.save()
    
    assert mock_ckpt.data["seen_studio_ids"] == ["s1", "s2"]
    db.commit.assert_called()
