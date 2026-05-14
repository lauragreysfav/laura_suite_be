import asyncio
import time


class TokenBucket:
    def __init__(self, capacity: int, rate: float) -> None:
        self.capacity = capacity
        self.rate = rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def try_consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                if self.try_consume():
                    return
            await asyncio.sleep(max(0.01, 1.0 / self.rate / 2))
