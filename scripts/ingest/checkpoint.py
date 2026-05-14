import json
import logging
from pathlib import Path

logger = logging.getLogger("ingest.checkpoint")

DEFAULTS = {
    "phase": "performers",
    "performers_prefix_idx": 0,
    "performers_page": 1,
    "seen_performer_ids": [],
    "seen_studio_ids": [],
    "studios_done": [],
    "studios_idx": 0,
    "scenes_studio_idx": 0,
    "scenes_page": 1,
}


class Checkpoint:
    def __init__(self, path: str = "ingest_checkpoint.json") -> None:
        self.path = path
        self._data = dict(DEFAULTS)
        self._dirty = False

    def load(self) -> None:
        p = Path(self.path)
        if p.exists():
            try:
                with open(p) as f:
                    raw = json.load(f)
                self._data = {**DEFAULTS, **raw}
                self._dirty = False
                logger.info(
                    "checkpoint_loaded", extra={"phase": self._data.get("phase")}
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "checkpoint_load_failed", extra={"error": str(e)}
                )

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)
            self._dirty = False
            logger.debug("checkpoint_saved")
        except OSError as e:
            logger.warning(
                "checkpoint_save_failed", extra={"error": str(e)}
            )

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        if self._data.get(key) != value:
            self._data[key] = value
            self._dirty = True

    def append(self, key: str, value) -> None:
        lst = self._data.setdefault(key, [])
        if value not in lst:
            lst.append(value)
            self._dirty = True
