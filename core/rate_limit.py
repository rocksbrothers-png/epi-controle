"""Rate limiting simples baseado em memória para endpoints críticos.

Utiliza sliding-window por IP. Adequado para instâncias únicas; para múltiplas
instâncias utilize Redis como backend (substituição futura).
"""

from __future__ import annotations

import os
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


# ── Fronteira de confiança da origem (R0) ────────────────────────────────────
#
# Quantos proxies CONFIÁVEIS existem entre o cliente e esta aplicação.
#
# A versão anterior lia `X-Forwarded-For.split(',')[0]` — o primeiro elemento,
# que é escrito pelo CLIENTE. Medido com limite 3: cabeçalho fixo deixava
# passar 3 de 6; variando o cabeçalho, passavam 6 de 6. Os quatro limitadores
# do projeto eram contornáveis com um header.
#
# A correção NÃO é trocar `[0]` por `[-1]`. Num encadeamento onde cada proxy
# ACRESCENTA (o `$proxy_add_x_forwarded_for` do nginx documentado em
# `docs/WEB_APP_URL_ARCHITECTURE.md`), o endereço observado pelo proxy mais
# interno fica na posição `-N`, com N = número de proxies confiáveis. `[-1]`
# acerta só quando N == 1 — e vira spoof quando N == 0, que é o caso de
# execução local e direta.
#
# Por isso a confiança é DECLARADA, não adivinhada.
#
# O padrão é 0: ignore o cabeçalho, use o peer do socket. É o único valor
# seguro na ausência de configuração, porque sem proxy na frente o cabeçalho é
# escolha do cliente. Uma implantação atrás de proxy que esqueça de declarar o
# valor falha FECHANDO — as origens colapsam num bucket e o excedente recebe
# 429 — em vez de falhar abrindo, que é justamente o defeito corrigido aqui.
# Falha fechada é barulhenta e reversível; falha aberta é silenciosa.
TRUSTED_PROXY_HOPS = max(0, int(os.environ.get('RATE_LIMIT_TRUSTED_PROXY_HOPS', '0') or 0))

_ORIGEM_INDETERMINADA = 'unknown'


def _peer_do_socket(handler) -> str:
    """Endereço da outra ponta da conexão TCP. Isto o cliente não escolhe."""
    try:
        return str(handler.client_address[0])
    except Exception:
        return _ORIGEM_INDETERMINADA


def get_client_ip(handler) -> str:
    """Origem para efeito de rate limiting.

    Aceita endereço encaminhado SOMENTE dentro da cadeia de proxies declarada.
    Fora dela, vale o peer do socket — e nenhum cabeçalho fornecido pelo
    cliente permite a ele escolher a própria identidade de limitação.
    """
    peer = _peer_do_socket(handler)
    if TRUSTED_PROXY_HOPS <= 0:
        return peer
    try:
        bruto = handler.headers.get('X-Forwarded-For', '') or ''
    except Exception:
        bruto = ''
    cadeia = [parte.strip() for parte in bruto.split(',') if parte.strip()]
    # Cadeia mais curta que a declarada: a requisição não atravessou os proxies
    # esperados, então nada nela prova origem. Vale o peer.
    if len(cadeia) < TRUSTED_PROXY_HOPS:
        return peer
    return cadeia[-TRUSTED_PROXY_HOPS]
