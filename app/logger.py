import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path("/data/logs")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        parts = [
            f'"timestamp":"{datetime.now(timezone.utc).isoformat()}"',
            f'"level":"{record.levelname}"',
            f'"logger":"{record.name}"',
            f'"module":"{record.module}"',
            f'"line":{record.lineno}',
            f'"message":"{record.getMessage().replace(chr(34), chr(39))}"',
        ]
        if record.exc_info and record.exc_info[0]:
            parts.append(f'"exception":"{self.formatException(record.exc_info).replace(chr(34), chr(39)).replace(chr(10), chr(92)+"n")}"')
        for key in ("task_id", "request_id", "user_id", "torrent_id", "job_id", "tracker_id", "scene_id", "elapsed_ms", "status", "error"):
            val = getattr(record, key, None)
            if val is not None:
                if isinstance(val, (int, float)):
                    parts.append(f'"{key}":{val}')
                else:
                    parts.append(f'"{key}":"{str(val).replace(chr(34), chr(39))}"')
        return "{" + ",".join(parts) + "}"


def setup_logging(level=logging.INFO):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    for h in root.handlers[:]:
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JSONFormatter())
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        str(LOG_DIR / "laura.log"),
        maxBytes=10*1024*1024,
        backupCount=5,
    )
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)

    error_handler = RotatingFileHandler(
        str(LOG_DIR / "error.log"),
        maxBytes=10*1024*1024,
        backupCount=10,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root.addHandler(error_handler)

    return root


logger = setup_logging()
