"""
Redis-backed per-site rate limiter.
Uses a sliding-window counter to enforce requests-per-minute limits
on each target eCourts domain.
"""
import time
import logging
from django.core.cache import caches

logger = logging.getLogger("django")


class RateLimiter:
    """Sliding-window rate limiter backed by Redis (via Django cache)."""

    def __init__(self, site_key: str, max_per_minute: int):
        self.site_key = f"ecourts_ratelimit:{site_key}"
        self.max_per_minute = max_per_minute
        self._cache = caches["default"]

    def acquire(self, timeout: float = 60.0) -> bool:
        """
        Block until a request slot is available, up to *timeout* seconds.
        Returns True if acquired, False if timed out.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._try_acquire():
                return True
            time.sleep(1.0)
        logger.warning("Rate limiter timeout for %s", self.site_key)
        return False

    def _try_acquire(self) -> bool:
        now = int(time.time())
        window_key = f"{self.site_key}:{now // 60}"
        try:
            current = self._cache.get(window_key, 0)
            if current < self.max_per_minute:
                self._cache.set(window_key, current + 1, timeout=120)
                return True
            return False
        except Exception:
            return True
