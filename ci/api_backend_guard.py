#!/usr/bin/env python3
"""Guarda de isolamento de backend (EST-V1.6-R1).

Contrato ÚNICO de validação (idêntico nos dois repositórios SaaS e Corporate);
o DADO que difere por produto é a allowlist em `ci/authorized_backend.json`.

Regra inegociável: um release nativo de um produto só pode apontar para o
backend autorizado DESSE produto. Backend do outro produto, ausente, vazio,
whitespace, não-HTTPS, loopback/localhost, com userinfo/fragment, ou host
apenas "parecido" (substring/sufixo) → ERRO, antes do build.

Comandos:
  resolve <input> : imprime (stdout) a URL autorizada a usar no build.
        input vazio → usa `api_base_url` da allowlist (backend do PRÓPRIO produto);
        input não-vazio → valida contra a allowlist e imprime; erro se não autorizado.
        Saída nonzero (falha o job) se a URL final não for autorizada.
        Apenas a URL vai para stdout — seguro para `$(...)`.
  validate <url>  : valida `url` contra a allowlist; exit 0 (OK) / 2 (REJECT).

A allowlist NÃO é a própria API_BASE_URL: é um arquivo versionado, por produto,
owner auditável. Comparar a variável consigo mesma não provaria isolamento.
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse

# Hosts de loopback/emulador — nunca válidos para release.
LOOPBACK_HOSTS = {
    'localhost', '127.0.0.1', '::1', '0.0.0.0', '10.0.2.2',
}

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWLIST = REPO_ROOT / 'ci' / 'authorized_backend.json'


def load_allowlist():
    data = json.loads(ALLOWLIST.read_text(encoding='utf-8'))
    product = str(data.get('product') or '').strip()
    primary = str(data.get('api_base_url') or '').strip()
    hosts = {str(h).strip().lower() for h in (data.get('authorized_hosts') or []) if str(h).strip()}
    if not product or not primary or not hosts:
        raise SystemExit(f'::error::allowlist inválida em {ALLOWLIST}')
    return product, primary, hosts


def validation_errors(url, authorized_hosts):
    """Lista de motivos de rejeição; vazia = autorizado."""
    reasons = []
    if url is None or str(url).strip() == '':
        return ['API_BASE_URL ausente/vazia']
    if url != url.strip():
        reasons.append('espaço em branco no início/fim')
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme != 'https':
        reasons.append(f"esquema deve ser https (recebido '{parts.scheme or '∅'}')")
    if parts.username or parts.password:
        reasons.append('userinfo (user:pass@) não permitido')
    if parts.fragment:
        reasons.append('fragmento (#...) não permitido')
    # hostname normaliza para minúsculas e remove porta; porta é tolerada mas
    # loopback e host não-autorizado são rejeitados.
    host = (parts.hostname or '').lower()
    if not host:
        reasons.append('host ausente')
    elif host in LOOPBACK_HOSTS:
        reasons.append(f"host de loopback '{host}' não permitido em release")
    elif host not in authorized_hosts:
        # Correspondência EXATA — nunca por substring/sufixo enganoso.
        reasons.append(
            f"host '{host}' não está na allowlist autorizada {sorted(authorized_hosts)}"
        )
    return reasons


def cmd_resolve(raw_input):
    product, primary, hosts = load_allowlist()
    chosen = (raw_input or '').strip() or primary  # vazio → backend do PRÓPRIO produto
    errors = validation_errors(chosen, hosts)
    if errors:
        print(
            f"::error::guard[{product}] rejeitou API_BASE_URL '{chosen}': "
            + '; '.join(errors),
            file=sys.stderr,
        )
        return 2
    print(chosen)  # ÚNICA saída em stdout
    return 0


def cmd_validate(url):
    product, _primary, hosts = load_allowlist()
    errors = validation_errors(url, hosts)
    if errors:
        print(f"REJECT[{product}] '{url}': " + '; '.join(errors), file=sys.stderr)
        return 2
    print('OK')
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ''
    arg = argv[2] if len(argv) > 2 else ''
    if cmd == 'resolve':
        return cmd_resolve(arg)
    if cmd == 'validate':
        return cmd_validate(arg)
    print('uso: api_backend_guard.py resolve|validate <url>', file=sys.stderr)
    return 64


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
