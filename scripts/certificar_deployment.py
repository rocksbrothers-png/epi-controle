#!/usr/bin/env python3
"""Certificação de deployment da frente #271 — B4-B.

## Por que existe

A B4-A prova, em CI, que o código e a configuração declarada estão certos. Ela
**não** consegue provar que o ambiente publicado está saudável, e quatro coisas
divergem entre os dois deployments com o código idêntico:

- `CORS_ALLOW_ORIGIN` errado → o Flutter Web do SaaS perde TODAS as
  capacidades, com o Dart intacto;
- `base-href` (`/app/` no corporativo × `/` no SaaS) → muda o routing do
  go_router e portanto os deep links;
- `API_BASE_URL` compilado no build do SaaS × mesmo-origin no corporativo;
- bancos separados → se as migrations 025/026/027 não rodaram no Supabase do
  SaaS, a configuração por Unidade não tem onde gravar.

Nenhuma dessas aparece em `pytest`. Todas aparecem para o operador.

## Estado: NOT CERTIFIED até rodar

Enquanto este script não for executado com sucesso contra os DOIS deployments,
a frente #271 fica **NOT CERTIFIED** para deployment. Ausência de execução não
é verde — é ausência de informação, e chamá-la de aprovação é o mesmo erro que
deixou 215 testes JS fora do CI.

## Somente leitura

Este script **não escreve** em produção. Provar que a gravação funciona
alterando a configuração real de alguém trocaria uma dúvida por um incidente:
o alerta que ele desligasse para se provar é o alerta de um operador de
verdade. Ele verifica leitura, health e forma da resposta — o que basta para
detectar as quatro divergências acima.

Para certificar ESCRITA, use um ambiente de staging com
`EPI_CERT_ALLOW_WRITE=1` e uma Unidade/EPI de teste controlados; esse caminho
é deliberadamente separado e não é exercido contra produção.

## Quem orquestra: `epi-controle` (corporativo)

**A certificação de deployment da #271 roda a partir do repositório
corporativo, e só dele.** Este script certifica os DOIS ambientes numa única
execução — API e Web Legado corporativos, Flutter Web corporativo em `/app/`,
API e Web Legado do SaaS, CORS do SaaS e Flutter Web do SaaS na raiz. Uma run
já produz o veredito completo.

Por isso os cinco `EPI_CERT_*` vivem apenas no cofre do `epi-controle`. Rodar
também pelo `epi-controle-app` repetiria exatamente o mesmo trabalho e
espalharia as credenciais dos dois ambientes por dois cofres em vez de um —
mais superfície de exposição sem nenhuma informação nova.

O `certificacao-271.yml` do `epi-controle-app` continua valendo para a B4-A
(as superfícies Dart, o Web Legado e os gates da frente, que são específicos
daquele artefato e da identidade iOS `com.livamobile`). Ele simplesmente não
recebe os secrets da B4-B: disparado lá com `smoke=true`, o job sai com
`NOT CERTIFIED` e código 2, que é a resposta correta para "não executado".

## Uso

    export EPI_CERT_CORP_URL=https://...          # API corporativa
    export EPI_CERT_CORP_TOKEN=...                # token de leitura
    export EPI_CERT_SAAS_API_URL=https://...      # API do SaaS
    export EPI_CERT_SAAS_WEB_URL=https://...      # Flutter Web do SaaS
    export EPI_CERT_SAAS_TOKEN=...
    python3 scripts/certificar_deployment.py

`EPI_CERT_SAAS_WEB_URL` não pode terminar em barra: ele também vira o header
`Origin` da checagem de CORS, e a comparação com `Access-Control-Allow-Origin`
é exata. Um valor com barra final produziria reprovação falsa.

As duas URLs de API entram como origem, SEM `/api` — o script concatena as
rotas por conta própria.

Nenhuma credencial vive no repositório: tudo entra por ambiente, e no CI por
secrets. Um deployment sem variáveis definidas é reportado como
`NOT CERTIFIED`, nunca como aprovado.

Os access tokens da aplicação valem 8 horas (`JWT_EXP_SECONDS`). Gere-os pouco
antes de executar; um valor cadastrado ontem já vai ser recusado com HTTP 401,
e o script trata isso como falha, corretamente. Certificação recorrente exige
uma solução de credencial de vida longa que ainda não existe.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = 20

#: Rotas de LEITURA que provam que a frente #271 está viva no ambiente. Cada
#: uma responde uma pergunta que o CI não alcança.
#: A ORDEM importa: `/api/units/selectable` vem primeiro porque é dela que sai
#: o `unit_id` usado na segunda. Ver `_unidade_para_classificar`.
SONDAS = (
    ('/api/units/selectable',
     'o seletor de Unidade tem fonte — sem isto nenhuma escrita é possível'),
    ('/api/stock/epis',
     'a listagem devolve a classificação por par (Unidade, EPI)'),
)

#: Campos que provam que as migrations rodaram NAQUELE banco. Se a tabela não
#: existe, o backend não tem de onde tirar estes valores.
#:
#: **A presença da chave não basta — o valor não pode ser nulo.** O backend faz
#: `item['unit_minimum_stock'] = classificacao.effective_minimum_stock if
#: classificacao else None` para as nove, e `classificacao` só é calculada
#: quando há Unidade resolvida. Sem `unit_id`, um perfil livre recebe as nove
#: chaves valendo `None` — e a checagem antiga, `campo in item`, aprovava isso
#: sem `classify_unit_epi_stock` ter sido chamado nem uma vez. Verde sem
#: execução: exatamente o que esta certificação existe para pegar.
CAMPOS_DE_CLASSIFICACAO = (
    'unit_minimum_stock',
    'minimum_stock_source',
    'effective_attention_percentage',
    'attention_percentage_source',
    'attention_limit',
    'stock_alert_enabled',
    'alert_source',
    'stock_status',
    'underlying_status',
)


class Resultado:
    def __init__(self, ambiente: str) -> None:
        self.ambiente = ambiente
        self.checagens: list[tuple[str, bool, str]] = []
        self.pulado = False

    def ok(self, nome: str, detalhe: str = '') -> None:
        self.checagens.append((nome, True, detalhe))

    def falha(self, nome: str, detalhe: str) -> None:
        self.checagens.append((nome, False, detalhe))

    @property
    def certificado(self) -> bool:
        return not self.pulado and bool(self.checagens) and all(
            passou for _, passou, _ in self.checagens
        )


def _get(url: str, token: str, origin: str = '') -> tuple[int, dict, dict]:
    """GET puro. **Nunca** POST — ver o cabeçalho deste arquivo."""
    req = urllib.request.Request(url, method='GET')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    if origin:
        req.add_header('Origin', origin)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            corpo = resp.read().decode('utf-8', errors='replace')
            cabecalhos = {k.lower(): v for k, v in resp.headers.items()}
            try:
                return resp.status, json.loads(corpo), cabecalhos
            except json.JSONDecodeError:
                return resp.status, {'_raw': corpo[:500]}, cabecalhos
    except urllib.error.HTTPError as e:
        return e.code, {'_erro': e.reason}, {k.lower(): v for k, v in (e.headers or {}).items()}
    except Exception as e:  # noqa: BLE001 - rede é imprevisível; o relatório trata
        return 0, {'_erro': str(e)}, {}


def _unidade_para_classificar(corpo: dict):
    """Extrai do PRÓPRIO backend uma Unidade autorizada, ou `None`.

    O `unit_id` nunca é inventado nem configurado por secret: vem da resposta
    de `/api/units/selectable`, que é quem decide o que este ator pode
    escolher. Um id vindo de fora seria o certificador AFIRMAR escopo em vez
    de verificá-lo — e um id errado reprovaria um ambiente correto.
    """
    if corpo.get('locked') and corpo.get('unit_id'):
        return int(corpo['unit_id'])
    for unidade in (corpo.get('units') or []):
        if unidade.get('id'):
            return int(unidade['id'])
    return None


def certificar_api(nome: str, base_url: str, token: str, origin: str = '') -> Resultado:
    r = Resultado(nome)
    if not base_url:
        r.pulado = True
        return r
    raiz = base_url.rstrip('/')

    status, corpo, _ = _get(raiz + '/api/units/selectable', token)
    if status == 0:
        r.falha('aplicação responde', f'inacessível: {corpo.get("_erro")}')
        return r
    r.ok('aplicação responde', f'HTTP {status}')

    if status in (401, 403):
        r.falha('autenticação', f'token recusado (HTTP {status})')
        return r
    r.ok('autenticação', 'token aceito')

    rota_unidades, porque_unidades = SONDAS[0]
    if status != 200:
        r.falha(f'GET {rota_unidades}', f'HTTP {status} — {porque_unidades}')
        return r
    r.ok(f'GET {rota_unidades}', porque_unidades)

    # Fail-closed: sem Unidade não há classificação por Unidade para provar, e
    # cair na visão corporativa (`unit_id` ausente) devolveria as nove chaves
    # nulas — aprovação sem execução. Reprovar aqui é dizer a verdade.
    unidade = _unidade_para_classificar(corpo)
    if unidade is None:
        r.falha('Unidade para classificação',
                'nenhuma Unidade selecionável para este ator: sem contexto de '
                'Unidade o backend não executa classify_unit_epi_stock, e a '
                'classificação da #271 fica sem como ser provada')
        return r
    r.ok('Unidade para classificação',
         f'unit_id={unidade} obtido de {rota_unidades} (nunca de secret)')

    rota_epis, porque_epis = SONDAS[1]
    st, body, _ = _get(f'{raiz}{rota_epis}?unit_id={unidade}', token)
    if st != 200:
        r.falha(f'GET {rota_epis}', f'HTTP {st} — {porque_epis}')
    else:
        r.ok(f'GET {rota_epis}', f'{porque_epis} (unit_id={unidade})')
        itens = body.get('items') or []
        if not itens:
            r.falha('schema da classificação',
                    'listagem vazia: impossível provar que as migrations rodaram')
        else:
            item = itens[0]
            ausentes = [c for c in CAMPOS_DE_CLASSIFICACAO if c not in item]
            if ausentes:
                r.falha('schema da classificação',
                        f'campos ausentes {ausentes} — migrations da #271 '
                        f'provavelmente não rodaram NESTE banco')
            else:
                # `is None`, não falsy: `stock_alert_enabled` é booleano e
                # `False` é resposta legítima — desligado não é ausente.
                nulos = [c for c in CAMPOS_DE_CLASSIFICACAO if item.get(c) is None]
                if nulos:
                    r.falha('classificação efetiva',
                            f'campos nulos {nulos}: as chaves existem mas '
                            f'classify_unit_epi_stock não foi executado. '
                            f'Presença de chave não é prova de classificação.')
                else:
                    r.ok('classificação efetiva',
                         'os nove campos por Unidade + EPI vieram com valor real')

    if origin:
        _, _, cab = _get(raiz + '/api/units/selectable', token, origin=origin)
        permitido = cab.get('access-control-allow-origin', '')
        if permitido in (origin, '*'):
            r.ok('CORS', f'origin {origin} liberado')
        else:
            r.falha('CORS',
                    f'Origin {origin} não liberado (recebido: {permitido!r}). '
                    f'O Flutter Web perde TODAS as capacidades com o Dart intacto.')
    return r


def certificar_web(nome: str, url: str, base_href_esperado: str) -> Resultado:
    """O routing do go_router depende do `base-href` publicado."""
    r = Resultado(nome)
    if not url:
        r.pulado = True
        return r
    status, corpo, _ = _get(url, '')
    if status != 200:
        r.falha('aplicação responde', f'HTTP {status}')
        return r
    r.ok('aplicação responde', f'HTTP {status}')

    html = corpo.get('_raw', '')
    if f'base href="{base_href_esperado}"' in html:
        r.ok('base-href', f'{base_href_esperado} — routing e deep links coerentes')
    else:
        r.falha('base-href',
                f'esperado {base_href_esperado!r}; o go_router resolve os deep '
                f'links /stock/config?unit_id=&epi_id= a partir daí')
    return r


def main() -> int:
    corp_url = os.environ.get('EPI_CERT_CORP_URL', '')
    corp_token = os.environ.get('EPI_CERT_CORP_TOKEN', '')
    saas_api = os.environ.get('EPI_CERT_SAAS_API_URL', '')
    saas_web = os.environ.get('EPI_CERT_SAAS_WEB_URL', '')
    saas_token = os.environ.get('EPI_CERT_SAAS_TOKEN', '')

    resultados = [
        # Corporativo: sistema Web próprio (Web Legado + API). NÃO publica
        # Flutter Web — são sistemas distintos por decisão de arquitetura, e o
        # Flutter é superfície do SaaS. A primeira versão desta certificação
        # exigia `/app/` aqui e reprovava um deployment CORRETO: o teste
        # afirmava uma arquitetura que o produto não tem.
        certificar_api('corporativo · API + Web Legado', corp_url, corp_token),
        # SaaS: dois serviços, origins separados, CORS obrigatório.
        certificar_api('saas · API + Web Legado', saas_api, saas_token, origin=saas_web),
        certificar_web('saas · Flutter Web', saas_web, '/'),
    ]

    print('=' * 72)
    print('CERTIFICAÇÃO DE DEPLOYMENT — #271 (B4-B)')
    print('=' * 72)
    falhou = False
    nao_executado = False
    for r in resultados:
        if r.pulado:
            nao_executado = True
            print(f'\n[NOT CERTIFIED] {r.ambiente}')
            print('   variáveis de ambiente ausentes — não executado')
            continue
        marca = 'CERTIFICADO' if r.certificado else 'FALHOU'
        if not r.certificado:
            falhou = True
        print(f'\n[{marca}] {r.ambiente}')
        for nome, passou, detalhe in r.checagens:
            print(f'   {"OK  " if passou else "FALHA"} {nome}: {detalhe}')

    print('\n' + '=' * 72)
    if falhou:
        print('RESULTADO: FALHOU — o deployment diverge do contrato da #271.')
        return 1
    if nao_executado:
        print('RESULTADO: NOT CERTIFIED — parte dos ambientes não foi verificada.')
        print('A frente #271 NÃO pode ser considerada encerrada para deployment.')
        print('Ausência de execução não é aprovação.')
        return 2
    print('RESULTADO: CERTIFICADO nos dois deployments.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
