"""Rate limiting simples baseado em memória para endpoints críticos.

Utiliza sliding-window por IP. Adequado para instâncias únicas; para múltiplas
instâncias utilize Redis como backend (substituição futura).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window rate limiter thread-safe em memória."""

    def __init__(self, max_calls: int, period_seconds: int):
        self._max = max_calls
        self._period = period_seconds
        self._windows: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._period
        with self._lock:
            window = self._windows[key]
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self._max:
                return False
            window.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        cutoff = now - self._period
        with self._lock:
            window = self._windows[key]
            while window and window[0] < cutoff:
                window.popleft()
            return max(0, self._max - len(window))

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)


# Instâncias globais pré-configuradas
login_limiter = RateLimiter(max_calls=10, period_seconds=60)
recovery_limiter = RateLimiter(max_calls=5, period_seconds=300)
tenant_limiter = RateLimiter(max_calls=60, period_seconds=60)
supplier_portal_limiter = RateLimiter(max_calls=30, period_seconds=60)


def get_client_ip(handler) -> str:
    """Extrai o IP real do cliente respeitando proxies."""
    forwarded = ''
    try:
        forwarded = handler.headers.get('X-Forwarded-For', '') or ''
    except Exception:
        pass
    if forwarded:
        return forwarded.split(',')[0].strip()
    try:
        return str(handler.client_address[0])
    except Exception:
        return 'unknown'
