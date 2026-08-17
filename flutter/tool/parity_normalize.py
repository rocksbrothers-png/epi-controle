#!/usr/bin/env python3
"""Normalização das diferenças LEGÍTIMAS entre `epi-controle` e `epi-controle-app`.

Paridade aqui é funcional e arquitetural, nunca igualdade byte a byte. Alguns
trechos **devem** diferir: identidade da aplicação, assinatura, deploy. Este
módulo troca cada um por um marcador canônico, para que dois arquivos que só
divergem nesses pontos produzam o mesmo hash.

É o coração do gate: normalizar de menos gera alarme falso a cada build; de
mais esconde drift real. Cada regra abaixo existe por um motivo escrito, e
acrescentar uma sem motivo é abrir um buraco no gate.
"""

from __future__ import annotations

import re

# (padrão, marcador, por quê)
REGRAS: tuple[tuple[str, str, str], ...] = (
    (
        r'com\.(?:livamobile|rocksbrothers)',
        '<ORG>',
        'prefixo da organização: cobre applicationId, bundle identifier, '
        'iosBundleId, namespace do pacote Kotlin e o --org do flutter create. '
        'É a identidade de cada repositório nas lojas e deve mesmo diferir.',
    ),
)

# Só o PREFIXO é normalizado, nunca o que vem depois: `<ORG>.epicontrole` e
# `<ORG>.outro` continuam distintos. Colapsar o sufixo junto faria dois pacotes
# diferentes produzirem o mesmo hash — o gate deixaria de ver uma troca real.

_COMPILADAS = tuple((re.compile(p), marcador) for p, marcador, _ in REGRAS)


def normalizar(conteudo: str) -> str:
    """Aplica as regras e devolve o conteúdo canônico.

    Não normaliza espaços em branco nem comentários de propósito: uma
    reformatação que só um dos repositórios recebeu **é** drift — ela faz o
    próximo diff entre os dois ficar ilegível, que é justamente o que trouxe a
    divergência de 33 arquivos até aqui sem ninguém notar.
    """
    for padrao, marcador in _COMPILADAS:
        conteudo = padrao.sub(marcador, conteudo)
    return conteudo


def descrever() -> str:
    return '\n'.join(f'  {marcador}  ← {motivo}' for _, marcador, motivo in REGRAS)


if __name__ == '__main__':
    print('Diferenças tratadas como legítimas pelo gate de paridade:\n')
    print(descrever())
