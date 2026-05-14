import asyncio
import time
import pytest
from scripts.ingest.rate_limiter import TokenBucket


def test_token_bucket_allows_burst():
    bucket = TokenBucket(capacity=5, rate=1.0)
    for _ in range(5):
        assert bucket.try_consume() is True


def test_token_bucket_blocks_when_empty():
    bucket = TokenBucket(capacity=2, rate=1.0)
    bucket.try_consume()
    bucket.try_consume()
    assert bucket.try_consume() is False


@pytest.mark.asyncio
async def test_acquire_waits_for_token():
    bucket = TokenBucket(capacity=1, rate=10.0)
    t0 = time.monotonic()
    await bucket.acquire()
    await bucket.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.09  # 1/10th second refill
