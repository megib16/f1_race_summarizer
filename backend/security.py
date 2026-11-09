"""Bounded per-process abuse protection. Use edge limits for multi-worker deployments."""
from collections import OrderedDict
from threading import Lock
import time


class RateLimiter:
    def __init__(self, requests_per_minute=120, max_clients=10000, clock=time.monotonic):
        if requests_per_minute < 1 or max_clients < 1:
            raise ValueError("Rate limits and client capacity must be positive")
        self.limit = requests_per_minute
        self.max_clients = max_clients
        self.clock = clock
        self.clients = OrderedDict()
        self.lock = Lock()

    def allow(self, client):
        now = self.clock()
        with self.lock:
            started, count = self.clients.pop(client, (now, 0))
            if now - started >= 60:
                started, count = now, 0
            allowed = count < self.limit
            self.clients[client] = (started, count + 1 if allowed else count)
            if len(self.clients) > self.max_clients:
                self.clients.popitem(last=False)
            return allowed
