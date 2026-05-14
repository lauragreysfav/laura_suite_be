from scripts.ingest.checkpoint import Checkpoint


def test_checkpoint_save_and_load(tmp_path):
    cp = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp.set("performers_prefix", "m")
    cp.set("performers_page", 5)
    cp.save()
    cp2 = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp2.load()
    assert cp2.get("performers_prefix") == "m"
    assert cp2.get("performers_page") == 5


def test_checkpoint_defaults():
    cp = Checkpoint(path="/tmp/nonexistent/ckpt.json")
    cp.load()
    assert cp.get("phase", "performers") == "performers"
    assert cp.get("seen_performer_ids", []) == []


def test_checkpoint_append(tmp_path):
    cp = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp.append("seen_studio_ids", "s1")
    cp.append("seen_studio_ids", "s2")
    cp.save()
    cp2 = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp2.load()
    assert cp2.get("seen_studio_ids") == ["s1", "s2"]
