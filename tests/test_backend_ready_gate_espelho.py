"""Espera de readiness no cold-start — proteção exclusiva deste repositório.

`static/app.js` deste repositório tem `waitForBackendReady()`, que sonda
`/health` antes de disparar `/api/bootstrap`. Ela existe porque no cold-start do
Render o backend leva dezenas de segundos rodando as funções de schema, e nessa
janela `/api/bootstrap` responde 503 — o que gerava uma tempestade de erros no
console (bootstrap + todos os loaders secundários).

**O repositório principal não tem essa função**, e é justamente por isso que
este teste existe.

A replicação entre os dois repositórios é feita copiando arquivos. Para o
Flutter isso é seguro: o gate de paridade (`flutter/tool/parity_manifest.json`)
exige conteúdo idêntico e reprova qualquer divergência. O backend é o oposto —
os dois repositórios divergem de propósito em vários arquivos, e o manifesto
não cobre nada fora de `flutter/`. Uma cópia integral de `static/app.js` vinda
do principal apaga esta função sem que teste nenhum perceba.

Foi o que aconteceu na fatia 1.1B: a função sumiu do `main` deste repositório e
só apareceu depois, numa auditoria. Nada quebrou em CI porque nada a cobria — a
falha seria em produção, e só no cold-start.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP_JS = RAIZ / 'static/app.js'


def _fonte() -> str:
    return APP_JS.read_text(encoding='utf-8')


def test_a_funcao_de_espera_existe():
    assert 'async function waitForBackendReady(' in _fonte(), (
        'waitForBackendReady sumiu de static/app.js — provavelmente por uma '
        'cópia integral do arquivo vinda do repositório principal, que não tem '
        'esta função. Restaure-a em vez de aceitar a remoção.'
    )


def test_a_funcao_e_efetivamente_chamada_antes_do_bootstrap():
    # Função presente mas não chamada é o mesmo defeito com aparência de código
    # saudável: o cold-start volta a disparar a tempestade de 503.
    fonte = _fonte()
    assert 'await waitForBackendReady();' in fonte, \
        'waitForBackendReady existe mas ninguém a chama'
    chamada = fonte.index('await waitForBackendReady();')
    bootstrap = fonte.index('loadBootstrap(', chamada)
    assert chamada < bootstrap, \
        'a espera precisa vir ANTES do bootstrap, senão não protege nada'


def test_a_sonda_usa_health_e_exige_ready_verdadeiro():
    fonte = _fonte()
    inicio = fonte.index('async function waitForBackendReady(')
    corpo = fonte[inicio:fonte.index('\n}\n', inicio)]
    assert "'/health'" in corpo, 'a sonda deixou de usar /health'
    # `/health` responde 200 mesmo durante o warmup: é o corpo que diz se está
    # pronto. Aceitar o 200 sozinho anularia a espera inteira.
    assert 'ready === true' in corpo, \
        'aceitar apenas o 200 de /health anula a espera: ele responde 200 no warmup'
    assert re.search(r'maxWaitMs|deadline', corpo), \
        'sem limite de tempo a espera trava a aplicação se o backend não subir'
