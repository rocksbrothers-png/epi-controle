#!/usr/bin/env python3
"""Gate de drift entre `epi-controle` e `epi-controle-app`.

## O problema que ele resolve

Uma divergência de 33 arquivos Dart cresceu entre os dois repositórios sem
ninguém notar, e só apareceu quando um gate de i18n tropeçou nela por acidente.
Nada no CI comparava os dois lados — porque nada podia: o CI de um repositório
não tem credencial para ler o outro.

## Como ele funciona sem acesso ao outro repositório

Por um MANIFESTO compartilhado. `tool/parity_manifest.json` lista os arquivos
que precisam permanecer funcionalmente sincronizados, cada um com o hash do seu
conteúdo **normalizado** (ver `parity_normalize.py`). O mesmo manifesto vive nos
dois repositórios.

O efeito é o que importa: mudar um arquivo sincronizado de um lado muda o hash,
e o CI do OUTRO lado passa a falhar até receber a mesma mudança. Não é preciso
que um repositório leia o outro — o manifesto é o contrato entre eles.

    editou aqui → regenera o manifesto → commita nos dois
                                       ↘ o outro repo fica vermelho até sincronizar

## O que ele deliberadamente NÃO faz

Não cobre arquivo que ainda não está em paridade. O manifesto começa com o que
já foi sincronizado e cresce a cada lote — um gate que exigisse paridade total
hoje nasceria vermelho e seria desligado na primeira semana. O que falta está
rastreado em `docs/PARIDADE_ESPELHO.md`, não aqui.

Uso:
    python3 tool/check_parity_drift.py            # verifica
    python3 tool/check_parity_drift.py --update   # regenera o manifesto
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parity_normalize import descrever, normalizar  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MANIFESTO = RAIZ / 'tool' / 'parity_manifest.json'


def _hash(caminho: pathlib.Path) -> str:
    conteudo = caminho.read_text(encoding='utf-8')
    return hashlib.sha256(normalizar(conteudo).encode('utf-8')).hexdigest()


def _carregar() -> dict:
    if not MANIFESTO.exists():
        print(f'❌ Manifesto ausente: {MANIFESTO}', file=sys.stderr)
        sys.exit(2)
    return json.loads(MANIFESTO.read_text(encoding='utf-8'))


def verificar() -> int:
    dados = _carregar()
    esperados: dict[str, str] = dados['files']
    ausentes, divergentes = [], []

    for relativo, hash_esperado in sorted(esperados.items()):
        caminho = RAIZ / relativo
        if not caminho.exists():
            ausentes.append(relativo)
            continue
        if _hash(caminho) != hash_esperado:
            divergentes.append(relativo)

    if not ausentes and not divergentes:
        print(f'✅ Paridade preservada em {len(esperados)} arquivos sincronizados.')
        return 0

    print('❌ Drift de paridade entre os repositórios.\n')
    if ausentes:
        print('Arquivos do manifesto que sumiram deste repositório:')
        for a in ausentes:
            print(f'   • {a}')
        print()
    if divergentes:
        print('Arquivos que divergiram do conteúdo acordado:')
        for d in divergentes:
            print(f'   • {d}')
        print()
    print('O que fazer:')
    print('  1. Se a mudança é intencional, aplique-a TAMBÉM no outro repositório.')
    print('  2. Rode `python3 tool/check_parity_drift.py --update` e commite o')
    print('     manifesto atualizado NOS DOIS repositórios.')
    print('  3. Se a diferença é legítima (identidade, assinatura, deploy), ela')
    print('     precisa de uma regra em tool/parity_normalize.py — com o motivo')
    print('     escrito — ou o arquivo sai do manifesto com justificativa.\n')
    print('Diferenças já tratadas como legítimas:')
    print(descrever())
    return 1


def atualizar() -> int:
    dados = _carregar()
    novos, sumidos = {}, []
    for relativo in sorted(dados['files']):
        caminho = RAIZ / relativo
        if not caminho.exists():
            sumidos.append(relativo)
            continue
        novos[relativo] = _hash(caminho)
    if sumidos:
        print('❌ Não dá para atualizar: arquivos do manifesto não existem aqui.')
        for s in sumidos:
            print(f'   • {s}')
        print('\nRemova-os do manifesto explicitamente se a saída foi intencional.')
        return 2
    dados['files'] = novos
    MANIFESTO.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    print(f'✅ Manifesto atualizado ({len(novos)} arquivos).')
    print('   Commite-o NOS DOIS repositórios, senão o outro lado fica vermelho.')
    return 0


if __name__ == '__main__':
    sys.exit(atualizar() if '--update' in sys.argv else verificar())
