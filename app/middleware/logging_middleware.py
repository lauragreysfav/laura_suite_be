import uuid
import time
import logging
from fastapi import Request

logger = logging.getLogger("laura.http")


async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()

    logger.info("request_start", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    })

    try:
        response = await call_next(request)
        elapsed = time.monotonic() - start
        logger.info("request_end", extra={
            "request_id": request_id,
            "status": response.status_code,
            "elapsed_ms": round(elapsed * 1000, 2),
        })
        return response
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.exception("request_error", extra={
            "request_id": request_id,
            "elapsed_ms": round(elapsed * 1000, 2),
            "error": str(e),
        })
        raise
