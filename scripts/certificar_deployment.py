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
    export EPI_CERT_SAAS_API_URL=https://...      # API do SaaS
    export EPI_CERT_SAAS_WEB_URL=https://...      # Flutter Web do SaaS

    # Modo NOVO (#313), por deployment — identidade `certification_readonly`:
    export EPI_CERT_CORP_USER=... EPI_CERT_CORP_PASSWORD=...
    export EPI_CERT_SAAS_USER=... EPI_CERT_SAAS_PASSWORD=...

    # Modo LEGADO, enquanto o novo não estiver provisionado:
    export EPI_CERT_CORP_TOKEN=...                # access JWT de 8 h
    export EPI_CERT_SAAS_TOKEN=...

    python3 scripts/certificar_deployment.py

Os modos são EXCLUSIVOS por deployment: com usuário e senha presentes o token
estático não é lido, e um login recusado REPROVA — nunca recorre ao JWT antigo.

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
uma solução de credencial de vida longa que ainda não existe (#313).

## Duas fases: preflight de disponibilidade, depois smoke funcional

Os serviços de aplicação hibernam por inatividade. Medido em 02/09/2026 abrindo
as URLs à mão: **46 s no corporativo, 35 s no SaaS** para a primeira resposta.
Contra `TIMEOUT = 20`, quatro execuções seguidas reprovaram com
`The read operation timed out` — e o timeout escondia dois defeitos reais, que
só apareceram quando os serviços foram aquecidos antes:

- os dois tokens estavam expirados (401 no SaaS, 403 no corporativo);
- um 503 era reportado como `autenticação: token aceito`, porque a checagem só
  reprovava em 401/403. O certificador AFIRMAVA ter verificado autenticação sem
  a requisição ter chegado à aplicação. O mesmo token saiu "aceito" numa leitura
  (503) e "recusado" na seguinte (403): não-determinismo sobre um fato que não é.

Daí a separação. O **preflight** só responde "a aplicação está PRONTA?". O
**smoke funcional** roda depois, com `TIMEOUT = 20` inalterado — dar mais tempo
para tudo transformaria cada checagem funcional numa espera longa e mascararia
lentidão real de endpoint.

## Por que "duas tentativas" não bastava — evidência de 03/09/2026

A primeira versão do preflight fazia duas tentativas de 60 s e chamava isso de
teto de 120 s. Contra os dois deployments de produção ela reprovou assim:

    preflight 1/2: HTTP 503 em 32.5s → nao_pronta
    preflight 2/2: HTTP 503 em  0.2s → nao_pronta

Os 0,2 s da segunda tentativa denunciam o erro de projeto. **O 503 não vem do
gateway: vem da própria aplicação.** `_require_bootstrap_ready` (`app.py`)
responde `DB_BOOTSTRAP_NOT_READY` a toda rota `/api/` não isenta enquanto
`state['ready']` for falso — e `ready` só vira verdadeiro quando o runner de
migrations termina. Nos logs de produção o `ensure_*` levou de ~50 s a mais de
90 s, sobre um cold start de contêiner de ~32 s.

Ou seja: "2 × 60 s" era orçamento de TIMEOUT, não de relógio. Uma resposta 503
imediata não consome timeout nenhum, então as duas tentativas coladas gastaram
32,6 s de espera real contra uma readiness de ~80 s a ~120 s. O contrato
classificava certo e nunca poderia passar.

## O contrato atual: amostragem periódica com deadline absoluto

O preflight sonda `/api/units/selectable` a cada `PREFLIGHT_INTERVALO`, até
`PREFLIGHT_DEADLINE` de **relógio monotônico**, com cada requisição limitada a
`PREFLIGHT_TIMEOUT`. Não é retry nem backoff: é esperar uma condição que se
resolve sozinha, com teto.

`/health` **não** serve como sonda: ele devolve 200 incondicionalmente durante o
boot (`runtime_probe_response` responde antes de olhar `ready`), que é como o
health check da plataforma mantém o serviço roteável enquanto o schema ainda
sobe. Sondar `/health` diria "pronta" em 32 s e jogaria o smoke funcional contra
503 — o mesmo falso verde que esta fase existe para eliminar. A sonda tem de ser
a superfície real.

O deadline não é permissão para esconder bootstrap lento: o relatório registra
`time_to_ready` por deployment. Se ele crescer, isso é evidência operacional
própria, não ruído a absorver.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

#: Timeout dos GETs FUNCIONAIS. Não subir: lentidão de endpoint é defeito, e
#: aumentar isto globalmente esconderia o defeito em vez de medi-lo.
TIMEOUT = 20

#: Timeout de CADA requisição do preflight, só dela. Dimensionado acima do cold
#: start medido (46 s no corporativo) — 45 s nasceria abaixo da evidência.
PREFLIGHT_TIMEOUT = 60

#: Orçamento ABSOLUTO de relógio por deployment, medido em `time.monotonic()`.
#: Não é a soma dos timeouts das requisições: um 503 respondido em 0,2 s não
#: consome timeout nenhum, e foi assim que "2 × 60 s" virou 32,6 s de espera
#: real contra um bootstrap que precisa de ~80 s a ~120 s.
PREFLIGHT_DEADLINE = 180

#: Intervalo entre sondagens. O preflight não é retry nem backoff: é amostragem
#: periódica de uma condição que se resolve sozinha (`state['ready']`).
PREFLIGHT_INTERVALO = 5

#: Vereditos do preflight. Existem como constantes para o gate exercitar a
#: classificação sem rede.
PRONTA = 'pronta'
PRONTA_AUTH_RECUSADA = 'pronta_auth_recusada'
CONTRATO_INVALIDO = 'contrato_invalido'
NAO_PRONTA = 'nao_pronta'


def _classificar_preflight(status: int) -> str:
    """"A aplicação acordou?" — função pura, um status por vez.

    O erro a evitar é o que o certificador cometia: tratar todo status != 0
    como "respondeu". Um 5xx é resposta do GATEWAY, não da aplicação, e foi
    exatamente assim que um 503 virou `token aceito`.

    · 2xx      a aplicação respondeu e aceitou
    · 401/403  a aplicação respondeu e recusou DELIBERADAMENTE — chegou à
               camada de autenticação, portanto está de pé
    · 404      respondeu, mas `/api/units/selectable` faz parte do contrato
               esperado: rota ausente é deployment errado, não indisponível.
               Falha imediata, sem nova sondagem — repetir não conserta
               contrato
    · 5xx      ainda não pronta. Inclui o 503 do PRÓPRIO backend: enquanto
               `state['ready']` é falso, `_require_bootstrap_ready` devolve
               `DB_BOOTSTRAP_NOT_READY` em toda rota `/api/` não isenta.
               Segue sondando até o deadline
    · 0        timeout ou erro de socket: nem resposta houve. Idem

    Demais 4xx (400, 429, …) contam como pronta pelo mesmo critério de
    401/403: são resposta deliberada da aplicação. O smoke funcional julga.
    """
    if 200 <= status < 300:
        return PRONTA
    if status in (401, 403):
        return PRONTA_AUTH_RECUSADA
    if status == 404:
        return CONTRATO_INVALIDO
    if status == 0 or status >= 500:
        return NAO_PRONTA
    return PRONTA


def _autenticou(status: int) -> bool:
    """Só 2xx é evidência de token aceito.

    A versão anterior reprovava apenas 401/403 e declarava "token aceito" para
    todo o resto — inclusive 500, 502, 503. Afirmar autenticação sobre uma
    resposta de gateway é alegar cobertura inexistente.
    """
    return 200 <= status < 300

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

#: Rota de autenticação. Literal e única — `/api/auth/login` é alias do MESMO
#: handler, mas NÃO está em `BOOTSTRAP_READY_EXEMPT_PATHS` e responderia 503
#: durante o boot. O gate estático exige exatamente esta constante.
ROTA_LOGIN = '/api/login'

#: Identidade do ator autenticado. Consultada ANTES do smoke funcional.
ROTA_IDENTIDADE = '/api/auth/me'

#: A identidade técnica da certificação (#313) e as duas permissões que ela
#: precisa ter — **exatamente** estas, nem mais nem menos. Continência aceitaria
#: uma conta com uma só, que reprovaria o smoke por falta de acesso e mandaria
#: investigar o deployment; e aceitaria um `registry_admin`, com as 26 escritas
#: que esta frente existe para não usar.
PAPEL_ESPERADO = 'certification_readonly'
PERMISSOES_ESPERADAS = frozenset({'units:view', 'stock:view'})

#: Modos de credencial, MUTUAMENTE EXCLUSIVOS. Nunca `login() or token`: um
#: fallback silencioso devolveria verde com a credencial que a #313 existe para
#: eliminar, e esconderia a falha do modo novo por semanas.
MODO_NOVO = 'credenciais'
MODO_LEGADO = 'token_estatico'
MODO_AUSENTE = 'sem_credencial'

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
        #: (numero, status, segundos, veredito) de cada sondagem do preflight.
        self.preflight: list[tuple[int, int, float, str]] = []
        #: Relógio absoluto do preflight inteiro. É evidência operacional por
        #: si só: se crescer, o bootstrap está degradando, e o deadline não
        #: pode servir para esconder isso.
        self.time_to_ready: float = 0.0
        #: Indisponibilidade NÃO é divergência de contrato. O relatório separa
        #: as duas porque a ação do operador é diferente em cada caso.
        self.nao_pronta = False

    def ok(self, nome: str, detalhe: str = '') -> None:
        self.checagens.append((nome, True, detalhe))

    def falha(self, nome: str, detalhe: str) -> None:
        self.checagens.append((nome, False, detalhe))

    @property
    def certificado(self) -> bool:
        return not self.pulado and bool(self.checagens) and all(
            passou for _, passou, _ in self.checagens
        )


def _get(url: str, token: str, origin: str = '',
         timeout: int = TIMEOUT) -> tuple[int, dict, dict]:
    """GET puro. **Nunca** POST — ver o cabeçalho deste arquivo.

    `timeout` é parâmetro para que o preflight use `PREFLIGHT_TIMEOUT` sem
    afrouxar os GETs funcionais. O default preserva `TIMEOUT` para quem não
    pedir nada — os funcionais não pedem, e um gate confere isso no ponto de
    chamada.
    """
    req = urllib.request.Request(url, method='GET')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    if origin:
        req.add_header('Origin', origin)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def _preflight(raiz: str, token: str = '') -> tuple[str, list, float]:
    """Fase 1: espera a aplicação ficar PRONTA. Somente GET, sem escrita.

    **Sem autenticação** (#313). O preflight responde uma pergunta só — "a
    aplicação saiu do bootstrap?" — e 401/403 já a responde: recusar
    deliberadamente prova que a requisição chegou à camada de autenticação.
    Mandar credencial aqui acoplaria readiness a identidade e obrigaria o login
    a acontecer ANTES do READY, que é justamente quando o banco pode não
    responder.

    O parâmetro `token` sobrevive com default vazio porque os 25 gates da #271
    o passam posicionalmente e uma das sabotagens de lá ancora no texto exato
    da linha do `_get`. Mudar a assinatura obrigaria a editar aquele arquivo —
    trocar a prova para acomodar o código. Em produção `certificar_api` chama
    `_preflight(raiz)` e nenhum header `Authorization` é emitido; há gate para
    isso.

    Amostragem periódica com deadline absoluto. A pergunta que governa a parada
    não é "quantas tentativas já fizemos" e sim "quanto tempo de RELÓGIO já
    esperamos" — contar tentativas foi o que fez a versão anterior desistir em
    32,6 s de um bootstrap de ~80 s, porque um 503 imediato não gasta timeout.

    Só `NAO_PRONTA` continua sondando. `CONTRATO_INVALIDO` (404) para na hora:
    repetir não conserta rota ausente. `PRONTA`/`PRONTA_AUTH_RECUSADA` param
    porque a resposta já é da aplicação.

    Devolve o veredito final, o registro cronometrado de cada sondagem e o
    `time_to_ready` total.
    """
    tentativas: list[tuple[int, int, float, str]] = []
    inicio_total = time.monotonic()
    veredito = NAO_PRONTA
    numero = 0

    while True:
        numero += 1
        inicio = time.monotonic()
        status, _, _ = _get(raiz + SONDAS[0][0], token,
                            timeout=PREFLIGHT_TIMEOUT)
        decorrido = time.monotonic() - inicio
        veredito = _classificar_preflight(status)
        tentativas.append((numero, status, decorrido, veredito))

        if veredito != NAO_PRONTA:
            break

        # Deadline ABSOLUTO: nenhuma sondagem nova começa depois dele. Uma
        # requisição já em voo pode terminar depois — isso é limitado por
        # `PREFLIGHT_TIMEOUT`, não por este laço. E o laço termina sempre: o
        # restante decresce a cada volta e a espera nunca o ultrapassa.
        restante = PREFLIGHT_DEADLINE - (time.monotonic() - inicio_total)
        if restante <= 0:
            break
        time.sleep(min(PREFLIGHT_INTERVALO, restante))

    return veredito, tentativas, time.monotonic() - inicio_total


def _modo(token: str, usuario: str, senha: str) -> str:
    """Qual credencial usar. Os modos são EXCLUSIVOS, por decisão de contrato.

    Com usuário e senha presentes o token estático não é sequer lido: se o
    login falhar, a certificação reprova. A alternativa — tentar o token antigo
    — devolveria verde usando exatamente a credencial que a #313 elimina, e a
    falha do caminho novo ficaria invisível até o JWT expirar.
    """
    if usuario and senha:
        return MODO_NOVO
    if token:
        return MODO_LEGADO
    return MODO_AUSENTE


def _login(raiz: str, usuario: str, senha: str) -> tuple[str, str]:
    """`POST /api/login` — a ÚNICA escrita do certificador. Devolve (token, erro).

    Nada aqui é registrado: nem usuário, nem senha, nem o token. O token volta
    como valor e vive só na variável local de quem chamou, pelo tempo do
    processo. Não vai a arquivo, `$GITHUB_ENV`, `$GITHUB_OUTPUT`, argumento de
    linha de comando nem log — o gate 14 varre o módulo atrás disso.

    Só é chamada DEPOIS do preflight declarar READY: `/api/login` é isento do
    portão de bootstrap, mas ainda consulta o banco, e tentar antes trocaria
    "credencial errada" por "banco ainda subindo" no relatório.
    """
    corpo = json.dumps({'username': usuario, 'password': senha}).encode('utf-8')
    req = urllib.request.Request(raiz + ROTA_LOGIN, data=corpo, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            dados = json.loads(resp.read().decode('utf-8', errors='replace'))
    except urllib.error.HTTPError as erro:
        try:
            detalhe = json.loads(erro.read().decode('utf-8', errors='replace'))
        except Exception:  # noqa: BLE001 - corpo de erro não estruturado
            detalhe = {}
        codigo = (detalhe.get('error') or {}).get('code') if isinstance(
            detalhe.get('error'), dict) else detalhe.get('code')
        return '', f'HTTP {erro.code}{" " + str(codigo) if codigo else ""}'
    except Exception as erro:  # noqa: BLE001 - rede
        return '', f'{type(erro).__name__}'
    token = str(dados.get('token') or '')
    if not token:
        return '', 'resposta 200 sem `token`: contrato de login divergente'
    return token, ''


def _validar_identidade(raiz: str, token: str) -> str:
    """`GET /api/auth/me` — quem é o ator, antes de tocar no smoke. '' = ok.

    Verificar o papel e as permissões aqui é o que separa "a credencial
    funciona" de "a credencial é a certa". Um `registry_admin` autenticaria e
    passaria o smoke inteiro carregando 26 permissões de escrita — a #313
    existe para que isso reprove, alto, na certificação.

    Igualdade e não continência: um conjunto a menos reprovaria o smoke adiante
    por falta de acesso, e mandaria investigar o deployment em vez da conta.
    """
    status, corpo, _ = _get(raiz + ROTA_IDENTIDADE, token)
    if status != 200:
        return f'HTTP {status} em {ROTA_IDENTIDADE}'
    dados = corpo.get('data') if isinstance(corpo.get('data'), dict) else corpo
    usuario = dados.get('user') or {}
    papel = str(usuario.get('role') or '')
    if papel != PAPEL_ESPERADO:
        return f'papel {papel!r}, esperado {PAPEL_ESPERADO!r}'
    permissoes = frozenset(dados.get('permissions') or ())
    if permissoes != PERMISSOES_ESPERADAS:
        sobrando = sorted(permissoes - PERMISSOES_ESPERADAS)
        faltando = sorted(PERMISSOES_ESPERADAS - permissoes)
        return (f'permissões divergem — sobrando {sobrando}, faltando {faltando}')
    if not str(usuario.get('company_id') or '').strip():
        return ('identidade sem empresa: o escopo de Unidade sairia vazio e o '
                'isolamento por tenant deixaria de ser verificável')
    return ''


def certificar_api(nome: str, base_url: str, token: str = '', origin: str = '',
                   usuario: str = '', senha: str = '') -> Resultado:
    r = Resultado(nome)
    if not base_url:
        r.pulado = True
        return r
    raiz = base_url.rstrip('/')

    modo = _modo(token, usuario, senha)
    if modo == MODO_AUSENTE:
        r.pulado = True
        return r

    # ── Fase 1: preflight, SEM credencial ──────────────────────────────────
    veredito, r.preflight, r.time_to_ready = _preflight(raiz)
    ultimo_status = r.preflight[-1][1]

    if veredito == NAO_PRONTA:
        # Fail-closed: nenhuma requisição funcional é emitida. Prosseguir
        # produziria exatamente as leituras enganosas que motivaram esta fase.
        r.nao_pronta = True
        r.falha('preflight',
                f'READY TIMEOUT: {len(r.preflight)} sondagem(ns) em '
                f'{r.time_to_ready:.1f}s, deadline de {PREFLIGHT_DEADLINE}s, '
                f'último HTTP {ultimo_status} — indisponibilidade, não '
                f'divergência de contrato')
        return r

    if veredito == CONTRATO_INVALIDO:
        r.falha('preflight',
                f'HTTP 404 em {SONDAS[0][0]} após {r.time_to_ready:.1f}s: o '
                f'servidor respondeu, mas a rota faz parte do contrato da '
                f'#271. Deployment ou roteamento errado — repetir não conserta')
        return r

    r.ok('preflight',
         f'aplicação pronta sem credencial: time_to_ready {r.time_to_ready:.1f}s '
         f'em {len(r.preflight)} sondagem(ns), HTTP {ultimo_status}')

    # ── Fase 1b: autenticação, só depois do READY ──────────────────────────
    if modo == MODO_NOVO:
        token, erro_login = _login(raiz, usuario, senha)
        if erro_login:
            # Fail-closed: nenhuma requisição funcional, e NENHUMA tentativa
            # com o token estático. Ver `_modo`.
            r.falha('autenticação', f'login recusado ({erro_login})')
            return r
        r.ok('autenticação', f'login aceito em {ROTA_LOGIN}')

        erro_identidade = _validar_identidade(raiz, token)
        if erro_identidade:
            r.falha('identidade', erro_identidade)
            return r
        r.ok('identidade',
             f'{PAPEL_ESPERADO} com exatamente {sorted(PERMISSOES_ESPERADAS)}')

    # ── Fase 2: smoke funcional, TIMEOUT inalterado ────────────────────────
    status, corpo, _ = _get(raiz + '/api/units/selectable', token)
    if status == 0:
        r.falha('aplicação responde',
                f'inacessível no smoke funcional apesar do preflight ter '
                f'passado: {corpo.get("_erro")}')
        return r
    r.ok('aplicação responde', f'HTTP {status}')

    if not _autenticou(status):
        if status in (401, 403):
            r.falha('autenticação', f'token recusado (HTTP {status})')
        else:
            r.falha('autenticação',
                    f'sem evidência de token aceito (HTTP {status}): a '
                    f'resposta não veio da camada de autenticação')
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
    corp_user = os.environ.get('EPI_CERT_CORP_USER', '')
    corp_pass = os.environ.get('EPI_CERT_CORP_PASSWORD', '')
    saas_api = os.environ.get('EPI_CERT_SAAS_API_URL', '')
    saas_web = os.environ.get('EPI_CERT_SAAS_WEB_URL', '')
    saas_token = os.environ.get('EPI_CERT_SAAS_TOKEN', '')
    saas_user = os.environ.get('EPI_CERT_SAAS_USER', '')
    saas_pass = os.environ.get('EPI_CERT_SAAS_PASSWORD', '')

    resultados = [
        # Corporativo: sistema Web próprio (Web Legado + API). NÃO publica
        # Flutter Web — são sistemas distintos por decisão de arquitetura, e o
        # Flutter é superfície do SaaS. A primeira versão desta certificação
        # exigia `/app/` aqui e reprovava um deployment CORRETO: o teste
        # afirmava uma arquitetura que o produto não tem.
        certificar_api('corporativo · API + Web Legado', corp_url, corp_token,
                       usuario=corp_user, senha=corp_pass),
        # SaaS: dois serviços, origins separados, CORS obrigatório.
        certificar_api('saas · API + Web Legado', saas_api, saas_token,
                       origin=saas_web, usuario=saas_user, senha=saas_pass),
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
        if r.nao_pronta:
            marca = 'NÃO ACORDOU'
        else:
            marca = 'CERTIFICADO' if r.certificado else 'FALHOU'
        if not r.certificado:
            falhou = True
        print(f'\n[{marca}] {r.ambiente}')
        for numero, status, segundos, veredito in r.preflight:
            print(f'   preflight {numero}/{len(r.preflight)}: HTTP {status} '
                  f'em {segundos:.1f}s → {veredito}')
        if r.preflight:
            print(f'   time_to_ready: {r.time_to_ready:.1f}s '
                  f'(deadline {PREFLIGHT_DEADLINE}s, sondagem a cada '
                  f'{PREFLIGHT_INTERVALO}s)')
        for nome, passou, detalhe in r.checagens:
            print(f'   {"OK  " if passou else "FALHA"} {nome}: {detalhe}')

    print('\n' + '=' * 72)
    if falhou:
        nao_acordaram = [r.ambiente for r in resultados if r.nao_pronta]
        if nao_acordaram:
            # Indisponibilidade e divergência de contrato pedem ações
            # diferentes do operador. Fundir as duas num veredito só foi o que
            # deixou quatro execuções indistinguíveis entre "dormindo" e
            # "quebrado".
            print(f'RESULTADO: FALHOU — READY TIMEOUT em '
                  f'{len(nao_acordaram)} deployment(s), com '
                  f'{PREFLIGHT_DEADLINE}s de deadline cada: '
                  f'{", ".join(nao_acordaram)}.')
            print('Isto é INDISPONIBILIDADE, não divergência de contrato: o')
            print('smoke funcional não chegou a ser executado nesses ambientes.')
        else:
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
