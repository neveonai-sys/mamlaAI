"""
Proxy rotation manager.
Supports a configurable pool of HTTP/SOCKS5 proxies.
Falls back to direct connection when no proxies are configured.
"""
import random
import time
import logging
import requests
from ecourts_scraper.constants import PROXY_POOL_URL

logger = logging.getLogger("django")


class ProxyManager:
    """Manages a rotating pool of proxies with health tracking."""

    def __init__(self):
        self._proxies: list[dict] = []
        self._unhealthy: dict[str, float] = {}
        self._cooldown_seconds = 300
        self._load_proxies()

    def _load_proxies(self):
        if not PROXY_POOL_URL:
            self._proxies = []
            return

        if PROXY_POOL_URL.startswith("http"):
            try:
                resp = requests.get(PROXY_POOL_URL, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                self._proxies = [
                    {"server": p["server"]} for p in data if "server" in p
                ]
            except Exception as e:
                logger.error("Failed to load proxy pool: %s", e)
                self._proxies = []
        else:
            for line in PROXY_POOL_URL.split(","):
                line = line.strip()
                if line:
                    self._proxies.append({"server": line})

        logger.info("Loaded %d proxies", len(self._proxies))

    def get_proxy(self) -> dict | None:
        """Return a random healthy proxy config dict for Playwright, or None."""
        if not self._proxies:
            return None

        now = time.time()
        healthy = [
            p for p in self._proxies
            if p["server"] not in self._unhealthy
            or (now - self._unhealthy[p["server"]]) > self._cooldown_seconds
        ]
        if not healthy:
            logger.warning("All proxies unhealthy, resetting health state")
            self._unhealthy.clear()
            healthy = self._proxies

        proxy = random.choice(healthy)
        return {"server": proxy["server"]}

    def mark_unhealthy(self, server: str):
        """Mark a proxy as temporarily unhealthy."""
        logger.warning("Marking proxy unhealthy: %s", server)
        self._unhealthy[server] = time.time()

    def mark_healthy(self, server: str):
        self._unhealthy.pop(server, None)

    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0
