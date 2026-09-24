#!/usr/bin/env python3
"""R0.5B — certificação da identidade da origem.

## O que este script responde

A R0.5 provou a FORMA da cadeia: a borda contribui com 3 elementos, e essa
contribuição não varia com o que o cliente envia. Isso refutou spoofing na rota
medida e não provou que `cadeia[-3]` represente quem originou a requisição.

Este script mede as quatro propriedades que faltam:

    P1  `cadeia[-N]` é o endereço que o próprio chamador observa como seu?
    P2  isso vale a partir de duas origens públicas realmente distintas?
    P3  `CF-Connecting-IP` e `True-Client-IP` são escritos pela borda, ou o
        cliente consegue controlá-los?
    P4  uma cadeia longa do cliente desloca ou trunca a janela que `cadeia[-N]`
        consome?

## Nada de endereço sai daqui

O endereço que você declara em `EPI_IDENT_MEU_IP` é ENVIADO à sonda para
comparação e **nunca impresso**. A sonda devolve só booleanos, contagens e
classificações. O relatório é seguro para colar em revisão.

## Duas origens, e o que não conta como duas

Origens **públicas distintas**. Não contam: duas execuções seguidas, dois
navegadores, dois aparelhos atrás do mesmo NAT, nem variar `X-Forwarded-For`.

A distinção é provada sem registrar endereço: na segunda origem você declara o
seu endereço **e** o da primeira, e a sonda responde os dois booleanos.

**E não basta declarar.** A primeira execução grava um COMPROMISSO local —
`scrypt(sal, endereço)`, com sal aleatório — e só o grava se P1 tiver sido
verdadeiro ali, em cada backend. A segunda execução recalcula o compromisso a
partir do que você declarou em `EPI_IDENT_IP_ANTERIOR` e exige que bata, com o
mesmo `N` e nos mesmos endpoints.

`scrypt` e não `sha256`: o sal impede tabela precomputada e não impede enumerar
2^32 endereços, e o roteiro manda levar o arquivo entre máquinas.

Sem isso, um endereço inventado (ou um erro de digitação) faria `p2_alt` dar
`False` e certificaria duas origens a partir de uma máquina só. Achado de
revisão, corrigido antes de qualquer medição valer.

O arquivo de estado fica FORA do repositório (`~/.r05b_origem_anterior.json`),
nunca é impresso, e some quando a certificação fecha.

## Uso

Primeira origem (ex.: rede de casa):

    $env:EPI_IDENT_CORP_URL = "https://epi-controle-app-gupy.onrender.com"
    $env:EPI_IDENT_CORP_KEY = "<a chave que você definiu no serviço>"
    $env:EPI_IDENT_SAAS_URL = "https://epi-controle-app-livamobile-api.onrender.com"
    $env:EPI_IDENT_SAAS_KEY = "<a chave do serviço SaaS>"
    $env:EPI_IDENT_ORIGEM   = "casa"
    $env:EPI_IDENT_MEU_IP   = "<o endereço público desta máquina>"
    python scripts/certificar_identidade_da_origem.py

Segunda origem, rede INDEPENDENTE (4G, outra operadora, máquina em outra
região) — acrescente o endereço da primeira:

    $env:EPI_IDENT_ORIGEM      = "4g"
    $env:EPI_IDENT_MEU_IP      = "<o endereço público DESTA máquina>"
    $env:EPI_IDENT_IP_ANTERIOR = "<o endereço público da primeira>"

Opcionais:

    $env:EPI_IDENT_ALT_URL  = "https://epi-controle.onrender.com"   # investigar
    $env:EPI_IDENT_ALT_KEY  = "<chave, se o serviço existir>"
    $env:EPI_IDENT_HOPS     = "3"                                   # default 3

## Uso — segunda origem

Leve o arquivo de estado junto se trocar de máquina. Mesma máquina em outra
rede (4G, tethering) não precisa: ele já está lá.

Saída: 0 = **P1, P2 e P4** satisfeitos nos DOIS backends · 1 = propriedade
reprovada, medições contraditórias ou backends discordantes · 2 = não executado
/ configuração incompleta / alvo inalcançável · 3 = medido numa origem, falta a
segunda · 4 = propriedades satisfeitas mas o ENCERRAMENTO falhou (o compromisso
não pôde ser apagado e continua reutilizável).

P3 **não** entra no veredito: ele classifica cabeçalhos, e a classificação é
reportada à parte. Um `sentinela_sobrevive` não reprova `HOPS`, mas é achado
grave por conta própria — o relatório o destaca.
"""

from __future__ import annotations

import hashlib
import ipaddress
import datetime
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROTA = '/api/origin-identity-diagnostics'
TIMEOUT = 30
REPETICOES = 3

# TEST-NET-1 (RFC 5737): documentação, não roteável, nunca emitido por
# infraestrutura real. Serve de sentinela justamente por isso.
SENTINELA_CF = '192.0.2.10'
SENTINELA_TC = '192.0.2.11'

#: SEGUNDA classe de sentinela para P3 (RFC 6598, CGNAT).
#:
#: Uma borda que higienize por FAIXA — descarta documentação, repassa o que
#: parece endereço público — devolve `substituida` para o sentinela de
#: documentação e ainda assim deixa o cliente escrever o cabeçalho. A
#: classificação diria "a borda escreve isto" onde a verdade é "a borda
#: descarta ISTO". Achado de revisão.
#:
#: CGNAT não é faixa de documentação e passa por validador que só conhece
#: RFC 5737, então separa os dois comportamentos. NÃO fecha o caso geral: uma
#: borda que higienize tudo que não é global continua sendo classificada como
#: `substituida`. Limitação registrada no §7 do contrato.
SENTINELA_CF_CGNAT = '100.64.0.10'
SENTINELA_TC_CGNAT = '100.64.0.11'

#: Tamanhos da cadeia do cliente no controle de P4.
#:
#: Uma amostra fixa de 30 elementos não sustenta veredito de PRODUÇÃO: uma
#: borda que preserve o sufixo em 30 e trunque em 300 passaria por P4 e ainda
#: deixaria `cadeia[-N]` cair em dado do cliente numa requisição maior — e
#: nada na aplicação limita o tamanho do `X-Forwarded-For`. Achado de revisão.
#:
#: A varredura procura a FRONTEIRA. Se algum tamanho quebrar a preservação, P4
#: reprova e o relatório nomeia o tamanho. Se a borda RECUSAR o tamanho com
#: status HTTP, isso é fronteira segura: acima dela o cliente não consegue nem
#: enviar a cadeia. Recusa por status é evidência; falha de rede não é, e
#: continua abortando a medição.
#: A lista sobe até muito além de qualquer limite de cabeçalho praticado
#: (122880 elementos ≈ 1,5 MB), porque parar num teto fixo é o mesmo defeito da
#: amostra fixa, só que maior: uma borda que trunque em 481 passaria por uma
#: varredura que para em 480. A varredura sobe até a borda RECUSAR — e aí a
#: faixa testada cobre tudo o que ela aceita. Achado de revisão.
TAMANHOS_DE_P4 = (1, 30, 120, 480, 1920, 7680, 30720, 122880)

#: Status que dizem ESPECIFICAMENTE "o que você mandou é grande demais". Só
#: estes fecham a fronteira de P4.
#:
#: `400` saiu daqui: é genérico. Um gateway que recuse por regra de WAF, por
#: conteúdo ou por qualquer outro motivo devolve 400 do mesmo jeito, e repetir
#: a requisição não estabelece a CAUSA — a repetição prova consistência, não
#: motivo. Tratar 400 como limite de tamanho fazia P4 passar por uma recusa
#: que não tem nada a ver com tamanho. Achado de revisão.
STATUS_DE_RECUSA_POR_TAMANHO = (413, 414, 431, 494)

#: Recusa que interrompe a escada mas NÃO prova fronteira de tamanho. A
#: varredura para, e P4 fica inconclusivo em vez de aprovado.
STATUS_DE_RECUSA_AMBIGUA = (400, 403, 501)


def _cadeia_de(tamanho: int) -> str:
    """Cadeia de cliente com `tamanho` elementos, toda de TEST-NET-1."""
    return ', '.join(f'192.0.2.{20 + (n % 200)}' for n in range(tamanho))

#: Campos cuja divergência entre repetições invalida a medição.
#:
#: Os três guardas de contaminação estão aqui porque são eles que decidem
#: `p1_contaminado`. Sem eles, repetições que concordassem em tamanho e em
#: candidato — mas divergissem em contaminação — passariam por idênticas, e o
#: script devolveria a primeira amostra, que por acaso parecia limpa. Achado de
#: revisão.
CAMPOS_DECISIVOS = (
    'cadeia_tamanho',
    'cadeia_suficiente_para_hops',
    'candidato_e_do_cliente',
    'sufixo_confiavel_preservado',
    'candidato_bate_com_origem_declarada',
    'candidato_bate_com_origem_alternativa',
    'prefixo_do_cliente_presente',
    'cadeia_maior_que_hops',
    'reivindicacao_fora_do_candidato',
    # A divergência entre a leitura da produção e a leitura completa, e a
    # canonicidade da chave de balde: se variarem entre repetições, a medição
    # não é de uma coisa só. Achado de revisão.
    'xff_instancias_repetidas',
    'candidato_ja_canonico',
    'cf_connecting_ip',
    'true_client_ip',
)

#: Contrato de tipo POR CAMPO, não só "é escalar".
#:
#: A primeira versão aceitava qualquer escalar, e `None` é escalar. Uma sonda
#: de versão diferente que OMITISSE `prefixo_do_cliente_presente` produziria
#: `None` via `.get()`, o campo passaria, e `medir` converteria a ausência em
#: `p1_contaminado = False` — um P1 sem guarda nenhuma certificaria. Achado de
#: revisão.
#:
#: Os dois `bate_com_*` são os únicos legitimamente nulos: valem `None` quando
#: o chamador não declarou endereço.
CAMPOS_BOOLEANOS = (
    'cadeia_suficiente_para_hops',
    'candidato_e_do_cliente',
    'sufixo_confiavel_preservado',
    'prefixo_do_cliente_presente',
    'cadeia_maior_que_hops',
    'reivindicacao_fora_do_candidato',
    'xff_instancias_repetidas',
    'candidato_ja_canonico',
)
CAMPOS_BOOLEANOS_OU_NULOS = (
    'candidato_bate_com_origem_declarada',
    'candidato_bate_com_origem_alternativa',
)
CAMPOS_INTEIROS = ('cadeia_tamanho', 'hops_avaliado')
CAMPOS_CLASSIFICADOS = ('cf_connecting_ip', 'true_client_ip')
CLASSES_VALIDAS = ('ausente', 'sentinela_sobrevive', 'substituida')

#: Estado que liga a segunda origem à primeira. Fica FORA do repositório de
#: propósito: não entra em commit por acidente, e o gate que varre endereços
#: reais nas superfícies da fatia continua valendo.
ESTADO_PADRAO = Path.home() / '.r05b_origem_anterior.json'
VERSAO_DO_ESTADO = 2


#: Cabeçalhos de RESPOSTA que identificam a camada que recusou. Lista fechada:
#: nenhum cabeçalho arbitrário entra no relatório.
CABECALHOS_DE_DIAGNOSTICO = (
    'server', 'content-type', 'cf-ray', 'cf-mitigated',
    'x-render-routing', 'retry-after',
)


def _diagnostico_do_erro(erro) -> str:
    """Descreve uma recusa HTTP o suficiente para saber DE QUEM ela é.

    A medição real devolveu `HTTP 403` nos dois backends e nada mais, e com
    isso não dava para distinguir a aplicação da borda — enquanto a
    aplicação, exercitada no caminho HTTP real, só devolve 200 ou 404. A
    resposta trazia a distinção nos cabeçalhos, e este script a descartava.

    O CORPO nunca sai daqui. A página de bloqueio da Cloudflare EXIBE o
    endereço do visitante, e o relatório é feito para ser colado numa
    revisão. Do corpo sai apenas se ele PARECE JSON ou HTML.
    """
    partes = [f'HTTP {erro.code} em {ROTA}']

    achados = {}
    try:
        for nome in CABECALHOS_DE_DIAGNOSTICO:
            valor = erro.headers.get(nome)
            if valor:
                achados[nome] = str(valor).strip()
    except Exception:  # noqa: BLE001 — resposta de erro arbitrária
        # Uma resposta de erro pode vir de qualquer camada, com um container de
        # cabeçalhos que não promete interface nenhuma. Sem pistas, o
        # diagnóstico sai como `indeterminado` — que é honesto — em vez de a
        # leitura derrubar a medição inteira.
        pass

    tipo = achados.get('content-type', '').lower()
    servidor = achados.get('server', '').lower()
    e_json = 'json' in tipo
    e_html = 'html' in tipo
    tem_marca_de_borda = bool(achados.get('cf-ray') or achados.get('cf-mitigated')
                              or 'cloudflare' in servidor
                              or achados.get('x-render-routing'))

    if tem_marca_de_borda or (e_html and not e_json):
        camada = 'borda'
    elif e_json:
        camada = 'aplicacao'
    else:
        camada = 'indeterminado'
    partes.append(f'recusa da camada: {camada}')

    if achados:
        partes.append('; '.join(f'{k}={v}' for k, v in sorted(achados.items())))

    if camada == 'borda':
        partes.append(
            'a aplicação não produz 403 nesta rota (200 com chave, 404 sem): '
            'quem recusou está à frente dela'
        )
    return ' | '.join(partes)


class NaoAlcancado(Exception):
    """Não deu para medir. Diferente de medir e reprovar.

    `http` guarda o status quando a borda RESPONDEU recusando. A varredura de
    P4 precisa distinguir "a borda recusou este tamanho" — que é fronteira
    medida, e segura — de "a rede falhou", que não é evidência de nada.
    """

    http = None


class Inconsistente(Exception):
    """Mediu, e as repetições se contradizem."""


class _RecusaRedirecionamento(urllib.request.HTTPRedirectHandler):
    """A chave viaja em cabeçalho, e o `urllib` COPIA cabeçalhos para o destino
    do redirecionamento — só `content-length` e `content-type` ficam de fora.
    Um redirect de canonicalização entregaria o segredo a outro host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NaoAlcancado(
            f'a URL respondeu com redirecionamento (HTTP {code}). Informe a URL '
            'final: este script não segue redirect para não expor a chave'
        )


_ABRIDOR = urllib.request.build_opener(_RecusaRedirecionamento)


def _cabecalho_valido(valor: str) -> bool:
    """O valor cabe num cabeçalho HTTP sem quebrar a requisição?

    `urllib` valida na hora de ENVIAR e levanta `ValueError: Invalid header
    value b'<valor>'` — com o valor inteiro dentro. Como a chave viaja em
    cabeçalho, esse texto levava o SEGREDO para `alvo.motivo`, que o relatório
    imprime e o operador cola. Conferir antes troca o vazamento por uma
    mensagem de configuração. Achado de revisão.
    """
    try:
        valor.encode('latin-1')
    except UnicodeEncodeError:
        return False
    return not any(c in valor for c in '\r\n\x00')


def _redigir(texto: str, *segredos: str) -> str:
    """Nenhum segredo sai daqui, venha de onde vier a mensagem.

    A conferência acima fecha o caminho conhecido; esta função fecha os que
    eu não previ. Qualquer exceção de rede que ecoe o cabeçalho passa por
    aqui antes de virar `motivo`.
    """
    limpo = str(texto)
    for segredo in segredos:
        if segredo and len(segredo) >= 4:
            limpo = limpo.replace(segredo, '[redigido]')
    return limpo


def _sondar(base_url: str, chave: str, hops: int, *, xff=None, cf=None,
            tc=None, reivindicacao='', alternativa='') -> dict:
    url = base_url.rstrip('/') + ROTA
    if not url.lower().startswith('https://'):
        raise NaoAlcancado('a URL precisa ser https — a chave viaja em cabeçalho')
    if not _cabecalho_valido(chave):
        raise NaoAlcancado(
            'a chave configurada tem caractere que não cabe em cabeçalho HTTP '
            '(quebra de linha, nulo ou fora de latin-1) — confira a variável '
            'de ambiente; o valor NÃO é mostrado aqui'
        )

    req = urllib.request.Request(url, method='GET')
    req.add_header('X-Diagnostics-Key', chave)
    req.add_header('X-Probe-Hops', str(hops))
    if reivindicacao:
        req.add_header('X-Origin-Claim', reivindicacao)
    if alternativa:
        req.add_header('X-Origin-Claim-Alt', alternativa)
    if xff is not None:
        req.add_header('X-Forwarded-For', xff)
    if cf is not None:
        req.add_header('CF-Connecting-IP', cf)
    if tc is not None:
        req.add_header('True-Client-IP', tc)

    try:
        with _ABRIDOR.open(req, timeout=TIMEOUT) as resp:
            corpo = resp.read().decode('utf-8', errors='replace')
            if resp.status != 200:
                raise NaoAlcancado(f'HTTP {resp.status} em {ROTA}')
            dados = json.loads(corpo)
            if not isinstance(dados, dict) or dados.get('probe') != 'R05B':
                raise NaoAlcancado(
                    'a resposta não é da sonda R0.5B — este host roda o mesmo '
                    'serviço, na versão com a sonda?'
                )
            return dados
    except urllib.error.HTTPError as e:
        if e.code == 404:
            erro = NaoAlcancado(
                'sonda desligada ou ausente (404) — o serviço precisa estar '
                'rodando a versão com a sonda E ter PROXY_CHAIN_PROBE_KEY'
            )
            erro.http = e.code
            raise erro from e
        erro = NaoAlcancado(_diagnostico_do_erro(e))
        erro.http = e.code
        raise erro from e
    except json.JSONDecodeError as e:
        raise NaoAlcancado('resposta não é JSON — este host serve a API?') from e
    except NaoAlcancado:
        raise
    except Exception as e:  # noqa: BLE001 — rede é imprevisível; vira relatório
        raise NaoAlcancado(_redigir(f'não alcançou o serviço: {e}',
                                    chave, reivindicacao, alternativa)) from e


def _forma(nome: str, amostra: dict) -> tuple:
    """Chave de comparação entre repetições, com os tipos conferidos.

    Uma sonda de versão diferente pode devolver o marcador certo e um campo
    decisivo malformado. Sem esta conferência, `{...}` levantaria `TypeError:
    unhashable type` fora de `NaoAlcancado`/`Inconsistente`, e o operador
    receberia traceback em vez de um dos códigos documentados.
    """
    def exigir(campo, condicao, esperado):
        if campo not in amostra:
            raise NaoAlcancado(
                f'controle {nome}: a resposta não trouxe {campo!r} — sonda de '
                'outra versão, ou resposta truncada'
            )
        if not condicao(amostra[campo]):
            raise NaoAlcancado(
                f'controle {nome}: {campo!r} veio como '
                f'{type(amostra[campo]).__name__}, esperado {esperado}'
            )

    for campo in CAMPOS_BOOLEANOS:
        exigir(campo, lambda v: isinstance(v, bool), 'booleano')
    for campo in CAMPOS_BOOLEANOS_OU_NULOS:
        exigir(campo, lambda v: v is None or isinstance(v, bool), 'booleano ou nulo')
    for campo in CAMPOS_INTEIROS:
        exigir(campo, lambda v: isinstance(v, int) and not isinstance(v, bool), 'inteiro')
    for campo in CAMPOS_CLASSIFICADOS:
        exigir(campo, lambda v: v in CLASSES_VALIDAS,
               f'uma de {CLASSES_VALIDAS}')

    return tuple(amostra[campo] for campo in CAMPOS_DECISIVOS)


def _canonico(endereco: str) -> str:
    """Forma canônica, igual à da sonda: o compromisso tem de bater entre as
    duas execuções mesmo que a grafia digitada mude."""
    try:
        alvo = ipaddress.ip_address(str(endereco).strip())
    except ValueError:
        return ''
    if alvo.version == 6 and alvo.ipv4_mapped is not None:
        alvo = alvo.ipv4_mapped
    return str(alvo)


#: Custo do compromisso. `scrypt` com estes parâmetros leva ~0,1 s e ~16 MB por
#: avaliação — irrelevante para as duas verificações que o roteiro faz, e
#: proibitivo para enumerar 2^32 endereços.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1


def _origem_plausivel(endereco: str) -> bool:
    """O endereço declarado pode ser uma origem PÚBLICA?

    O contrato exige duas origens públicas distintas. Só validar a sintaxe
    aceitava RFC 1918, loopback, CGNAT — e dois candidatos privados podem
    satisfazer as duas execuções sem que haja duas origens públicas, além de
    se repetirem entre redes não relacionadas. Achado de revisão.

    `is_global` é o teste forte, e ele recusa também CGNAT (100.64.0.0/10),
    que `is_private` deixaria passar.

    As faixas de documentação (RFC 5737, RFC 3849) foram aceitas por uma versão
    desta função, para os gates poderem exercitar `main()` sem escrever endereço
    real nas superfícies da fatia. Era enfraquecer a validação de PRODUÇÃO por
    conveniência de teste: um placeholder esquecido em `EPI_IDENT_MEU_IP`
    produziria certificação a partir de endereço não roteável. Achado de
    revisão. Os gates que exercitam `main()` agora substituem esta função; o
    gate que testa a função usa os endereços de verdade.
    """
    try:
        alvo = ipaddress.ip_address(str(endereco).strip())
    except ValueError:
        return False
    if alvo.version == 6 and alvo.ipv4_mapped is not None:
        alvo = alvo.ipv4_mapped
    # `is_global` é True para MULTICAST em CPython (224.0.0.0/4, ff00::/8).
    # Multicast não é origem de ninguém, e o gate pegou isso. Reservado e
    # não-especificado entram na mesma recusa.
    if alvo.is_multicast or alvo.is_reserved or alvo.is_unspecified:
        return False
    return bool(alvo.is_global)


def _compromisso(sal_hex: str, endereco: str) -> str:
    """Compromisso com o endereço, de custo deliberadamente alto.

    A primeira versão usava `sha256(sal || endereço)`. O sal impede tabela
    precomputada e **não** impede enumeração: IPv4 tem 2^32 valores, e quem
    tivesse o arquivo — que o roteiro manda levar de uma máquina para outra —
    recuperaria o endereço em segundos. Isso contradizia a premissa do
    instrumento, que é não registrar endereço. Achado de revisão.

    `scrypt` não torna a recuperação impossível; torna o custo proibitivo, e é
    memória-dura, então GPU não ajuda como ajudaria com SHA-256. Somado a isso,
    o arquivo é local e some quando a certificação fecha.
    """
    canonico = _canonico(endereco)
    if not canonico:
        return ''
    bruto = hashlib.scrypt(canonico.encode('utf-8'), salt=bytes.fromhex(sal_hex),
                           n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return bruto.hex()


def _controle(nome: str, **kwargs) -> dict:
    """Repete a mesma sondagem e exige que as repetições concordem.

    A R0.5 aprendeu isso da pior forma: uma requisição só não distingue medição
    de coincidência.
    """
    amostras = [_sondar(**kwargs) for _ in range(REPETICOES)]

    # A sonda pode ter avaliado OUTRO N: `_hops_pedido` satura em
    # `HOPS_MAXIMO`, e uma versão diferente pode interpretar o cabeçalho de
    # outro jeito. Certificar a janela errada é certificar nada. Achado de
    # revisão.
    pedido = kwargs.get('hops')
    for amostra in amostras:
        if amostra.get('hops_avaliado') != pedido:
            raise NaoAlcancado(
                f'controle {nome}: pedi hops={pedido} e a sonda avaliou '
                f'hops={amostra.get("hops_avaliado")} — janela diferente da '
                'que seria aplicada'
            )

    formas = {_forma(nome, a) for a in amostras}
    if len(formas) != 1:
        raise Inconsistente(
            f'controle {nome}: {len(formas)} respostas diferentes em '
            f'{REPETICOES} sondagens — há mais de um caminho de borda'
        )
    return amostras[0]


class Alvo:
    def __init__(self, nome: str, url: str, chave: str) -> None:
        self.nome, self.url, self.chave = nome, url, chave
        self.alcancado = False
        self.motivo = ''
        self.contradicao = False
        self.p1 = None
        self.p1_contaminado = None
        self.p2_alt = None
        self.anterior_ligado = None
        self.p3_cf = None
        self.p3_tc = None
        self.xff_duplicado = None
        self.candidato_canonico = None
        self.p4_maior_testado = 0
        self.p4_quebrou_em = None
        self.p4_recusada_em = None
        self.p4_ambigua_em = None
        self.p4_nao_chegou_em = None
        self.p4 = None
        self.candidato_do_cliente = None

    @property
    def configurado(self) -> bool:
        return bool(self.url and self.chave)


#: Precedência entre classificações de P3, da mais conservadora para a que
#: licencia adoção. `substituida` é a ÚNICA que diz "a borda escreve este
#: cabeçalho", então só vale por unanimidade: qualquer outra observação vence.
PRECEDENCIA_P3 = ('sentinela_sobrevive', 'ausente', 'substituida')


def _classe_conservadora(*classes) -> str:
    """A classificação que menos licencia adotar o cabeçalho."""
    vistas = [c for c in classes if c]
    if not vistas:
        return None
    for classe in PRECEDENCIA_P3:
        if classe in vistas:
            return classe
    return vistas[0]


def _confirmar_recusa(comum: dict, meu_ip: str, tamanho: int) -> None:
    """A recusa tem de se REPETIR para valer como fronteira.

    `_controle` aborta na primeira exceção e não chega a comparar as
    `REPETICOES`. Uma recusa isolada pode ser outra rota de borda, ou resposta
    transitória — e registrá-la como fronteira segura faria P4 passar sem ter
    detectado o caminho que ACEITA o mesmo tamanho. Achado de revisão.

    Se alguma repetição aceita o que outra recusou, não existe fronteira:
    existe contradição, e contradição já é fatal no instrumento.
    """
    for _ in range(REPETICOES):
        try:
            _sondar(**comum, xff=_cadeia_de(tamanho), reivindicacao=meu_ip)
        except NaoAlcancado as e:
            if e.http in STATUS_DE_RECUSA_POR_TAMANHO:
                continue
            raise
        raise Inconsistente(
            f'cadeia de {tamanho} elementos: uma sondagem foi RECUSADA e outra '
            'foi ACEITA — há mais de um caminho de borda para a mesma '
            'requisição, e aí não existe fronteira, existe contradição'
        )


def _varrer_p4(comum: dict, meu_ip: str) -> tuple:
    """P4 em vários tamanhos de cadeia, procurando a fronteira.

    Devolve `(ok, maior_testado, quebrou_em, recusada_em, ambigua_em,
    nao_chegou_em, amostras)`.

    Uma amostra única não sustenta veredito de produção: a preservação pode
    valer em 30 elementos e quebrar em 300, e aí `cadeia[-N]` cai em dado do
    cliente numa requisição que a aplicação aceita do mesmo jeito.
    """
    maior_testado, quebrou_em, recusada_em = 0, None, None
    ambigua_em, nao_chegou_em = None, None
    amostras = []
    for tamanho in TAMANHOS_DE_P4:
        try:
            amostra = _controle(f'P4 (cadeia de {tamanho})', **comum,
                                xff=_cadeia_de(tamanho), reivindicacao=meu_ip)
        except NaoAlcancado as e:
            # Recusa POR STATUS DE TAMANHO é fronteira medida: acima dela o
            # cliente não consegue nem enviar a cadeia.
            if e.http in STATUS_DE_RECUSA_POR_TAMANHO and maior_testado:
                _confirmar_recusa(comum, meu_ip, tamanho)
                recusada_em = tamanho
                break
            # Recusa genérica interrompe a escada sem provar nada sobre
            # tamanho: P4 fica INCONCLUSIVO, não aprovado. Achado de revisão.
            if e.http in STATUS_DE_RECUSA_AMBIGUA and maior_testado:
                ambigua_em = tamanho
                break
            # Falha de rede não é evidência de nada e aborta a medição.
            raise
        amostras.append(amostra)
        # A propriedade de P4 vem PRIMEIRO. Uma borda que trunca de verdade
        # devolve cadeia curta E sufixo destruído; diagnosticar isso como
        # "não chegou" trocaria o achado certo por outro. A primeira versão
        # desta rodada invertia a ordem e o gate `R05B-47` me corrigiu.
        if not (amostra.get('sufixo_confiavel_preservado')
                and not amostra.get('candidato_e_do_cliente')
                and amostra.get('candidato_bate_com_origem_declarada') is True):
            quebrou_em = tamanho
            break
        # Sufixo intacto: mas a cadeia CHEGOU? Se a borda filtra faixa de
        # documentação, todo elemento enviado some antes da sonda, o sufixo
        # aparece intacto em qualquer tamanho e P4 certifica sem ter testado
        # nada. A amostra que não chega não é evidência. Achado de revisão.
        if int(amostra.get('cadeia_tamanho') or 0) <= tamanho:
            nao_chegou_em = tamanho
            break
        maior_testado = tamanho
    # Sem RECUSA, a faixa testada não tem topo provado, e a propriedade de P4 é
    # sobre TODA requisição que a aplicação aceita. A 11ª rodada trocou a
    # amostra fixa por uma escada com teto e eu declarei isso aprovado com
    # ressalva — era o mesmo erro uma casa adiante, e a revisão está certa:
    # teto fixo é amostra fixa. Sem fronteira, o resultado é INCONCLUSIVO.
    #
    # Fechar isso de verdade exige limite de tamanho na APLICAÇÃO, que é
    # decisão do autor e não está autorizada aqui.
    ok = (quebrou_em is None and ambigua_em is None and nao_chegou_em is None
          and recusada_em is not None)
    return ok, maior_testado, quebrou_em, recusada_em, ambigua_em, nao_chegou_em, amostras


def medir(alvo: Alvo, hops: int, meu_ip: str, ip_anterior: str) -> None:
    comum = dict(base_url=alvo.url, chave=alvo.chave, hops=hops)
    try:
        # P1 — SEM `X-Forwarded-For`. É essa ausência que garante que toda a
        # cadeia recebida foi escrita pela borda, e que a reivindicação não
        # pode ter sido usada para construir o candidato.
        identidade = _controle('P1 (identidade)', **comum,
                               reivindicacao=meu_ip, alternativa=ip_anterior)

        # P3 com as DUAS classes de sentinela. Uma borda que higienize só as
        # faixas de documentação devolveria `substituida` para o sentinela de
        # RFC 5737 e deixaria o cliente controlar o cabeçalho assim mesmo.
        cf_doc = _controle('P3 (CF-Connecting-IP, documentação)',
                           **comum, cf=SENTINELA_CF)
        cf_cgnat = _controle('P3 (CF-Connecting-IP, CGNAT)',
                             **comum, cf=SENTINELA_CF_CGNAT)
        tc_doc = _controle('P3 (True-Client-IP, documentação)',
                           **comum, tc=SENTINELA_TC)
        tc_cgnat = _controle('P3 (True-Client-IP, CGNAT)',
                             **comum, tc=SENTINELA_TC_CGNAT)
        # P4 declara a origem TAMBÉM. Sem isso, o controle só perguntava se o
        # sufixo sobreviveu — e `cadeia[-N]` podia ter virado um proxy
        # compartilhado na rota com cadeia longa, sem sentinela nenhuma. P1
        # passaria na rota sem cabeçalho, P4 passaria com outro candidato, e a
        # certificação sairia com as requisições de cadeia longa colapsando num
        # balde só. É a distinção B/C do §4, dentro do próprio controle.
        (p4_ok, p4_maior, p4_quebrou, p4_recusa, p4_ambigua,
         p4_nao_chegou, p4_amostras) = _varrer_p4(comum, meu_ip)
    except NaoAlcancado as e:
        alvo.motivo = str(e)
        return
    except Inconsistente as e:
        alvo.alcancado = True
        alvo.contradicao = True
        alvo.motivo = str(e)
        return

    alvo.alcancado = True
    alvo.p1 = identidade.get('candidato_bate_com_origem_declarada')
    alvo.p2_alt = identidade.get('candidato_bate_com_origem_alternativa')
    alvo.candidato_do_cliente = identidade.get('candidato_e_do_cliente')
    # As duas guardas do LIMITADOR valem para TODA amostra, não só para P1.
    #
    # A requisição de P1 não manda `X-Forwarded-For`. Uma borda que só
    # acrescente uma segunda instância QUANDO o cliente manda a dele produziria
    # `xff_instancias_repetidas=false` em P1 e `true` em todas as de P4 — e o
    # veredito, olhando só P1, certificaria. O mesmo vale para a canonicidade:
    # a rota da cadeia longa pode escrever outra grafia. Achado de revisão.
    todas = [identidade, cf_doc, cf_cgnat, tc_doc, tc_cgnat] + list(p4_amostras)
    alvo.xff_duplicado = any(
        a.get('xff_instancias_repetidas') is not False for a in todas)
    alvo.candidato_canonico = all(
        a.get('candidato_ja_canonico') is True for a in todas)

    # Contaminação: os três guardas juntos. Se qualquer um disparar, P1 não é
    # evidência de nada — o candidato pode ter vindo do que o chamador enviou.
    alvo.p1_contaminado = bool(
        identidade.get('prefixo_do_cliente_presente')
        or identidade.get('cadeia_maior_que_hops')
        or identidade.get('reivindicacao_fora_do_candidato')
    )

    # A classificação que vale é a MAIS CONSERVADORA entre as duas classes:
    # `substituida` é a única que licencia adotar o cabeçalho, então exige
    # unanimidade.
    alvo.p3_cf = _classe_conservadora(cf_doc.get('cf_connecting_ip'),
                                      cf_cgnat.get('cf_connecting_ip'))
    alvo.p3_tc = _classe_conservadora(tc_doc.get('true_client_ip'),
                                      tc_cgnat.get('true_client_ip'))
    alvo.p4 = p4_ok
    alvo.p4_maior_testado = p4_maior
    alvo.p4_quebrou_em = p4_quebrou
    alvo.p4_recusada_em = p4_recusa
    alvo.p4_ambigua_em = p4_ambigua
    alvo.p4_nao_chegou_em = p4_nao_chegou


def _caminho_do_estado() -> Path:
    bruto = os.environ.get('EPI_IDENT_ESTADO', '').strip()
    return Path(bruto) if bruto else ESTADO_PADRAO


def _host_canonico(host: str) -> str:
    """Host canônico, com colchetes de volta quando o literal é IPv6.

    Literal de endereço tem mais de uma grafia para o MESMO destino: a forma
    comprimida e a expandida do mesmo IPv6, e `::ffff:<v4>` e `<v4>`. Comparar
    a grafia deixava DUAS grafias do mesmo endpoint passarem por dois backends
    distintos — exatamente o que a conferência de distinção existe para
    impedir, e a mesma classe do achado da porta padrão.

    Os colchetes voltam porque `partes.hostname` os remove: sem eles a
    autoridade reconstruída não diz onde o endereço acaba e a porta começa
    (`https://::1:8443`), e endpoints DIFERENTES colidiriam na comparação.
    Achado de revisão.
    """
    try:
        alvo = ipaddress.ip_address(host)
    except ValueError:
        # Nome de host: o ponto-raiz é opcional no DNS. `example.com` e
        # `example.com.` resolvem para o mesmo lugar, e preservá-lo deixava o
        # MESMO deployment passar pelos dois backends obrigatórios. Achado de
        # revisão.
        return host.rstrip('.')
    if alvo.version == 6 and alvo.ipv4_mapped is not None:
        alvo = alvo.ipv4_mapped      # mesma canonicalização que a sonda faz
    return f'[{alvo}]' if alvo.version == 6 else str(alvo)


def _normalizar_url(url: str) -> str:
    """Forma canônica de URL, para comparar ENDPOINT e não grafia.

    `https://host` e `https://host:443` vão para o mesmo lugar, e comparar
    texto cru os trataria como distintos — o que deixava dois backends
    "distintos" serem o mesmo deployment. Achado de revisão.
    """
    bruto = str(url or '').strip()
    if not bruto:
        return ''
    try:
        partes = urllib.parse.urlsplit(bruto)
    except ValueError:
        # IPv6 malformado (`https://[`) faz `urlsplit` levantar. Sem isto saía
        # traceback com status 1 — o mesmo de uma propriedade reprovada — antes
        # de qualquer sondagem. Achado de revisão.
        return ''
    esquema = (partes.scheme or '').lower()
    host = _host_canonico((partes.hostname or '').lower())
    try:
        porta = partes.port
    except ValueError:
        porta = None
    if porta is None or (esquema, porta) in (('https', 443), ('http', 80)):
        autoridade = host
    else:
        autoridade = f'{host}:{porta}'
    caminho = (partes.path or '').rstrip('/')
    return f'{esquema}://{autoridade}{caminho}'


def _gravar_estado(origem: str, hops: int, meu_ip: str, nomes_ok: list,
                   urls: dict, p3: dict = None) -> Path:
    """Compromisso da primeira origem. Só é chamado com P1 limpo.

    Guarda o que a segunda execução precisa para PROVAR que o endereço
    declarado em `EPI_IDENT_IP_ANTERIOR` foi mesmo medido aqui — e não apenas
    digitado lá.
    """
    sal = secrets.token_hex(32)
    caminho = _caminho_do_estado()
    caminho.write_text(json.dumps({
        'versao': VERSAO_DO_ESTADO,
        'origem': origem,
        'hops': hops,
        'sal': sal,
        'compromisso': _compromisso(sal, meu_ip),
        'backends_com_p1': sorted(nomes_ok),
        # Os rótulos `corporativo`/`saas` são estáticos: sem as URLs, trocar um
        # endpoint entre a origem A e a B deixaria combinar P1 de um serviço com
        # P2 de outro. Achado de revisão. As URLs já saem no relatório, então
        # guardá-las aqui não acrescenta exposição.
        'urls': {nome: _normalizar_url(url) for nome, url in urls.items()},
        # P3 da PRIMEIRA origem. Sem isto, um `sentinela_sobrevive` observado
        # em A desaparecia do relatório final: a segunda execução só mostrava a
        # classificação dela, e o operador podia fechar o contrato adotando um
        # cabeçalho que o cliente controla na outra rota. Achado de revisão.
        'p3': dict(p3 or {}),
        # Instante da medição. Não expira nada por conta própria — o prazo é
        # decisão do autor —, mas deixa a IDADE da evidência visível no
        # relatório em vez de invisível. Achado de revisão.
        'instante': datetime.datetime.now(datetime.timezone.utc)
                            .replace(microsecond=0).isoformat(),
    }, indent=2), encoding='utf-8')
    return caminho


ESQUEMA_DO_ESTADO = {
    'origem': str,
    'hops': int,
    'sal': str,
    'compromisso': str,
    'backends_com_p1': list,
    'urls': dict,
    'p3': dict,
    'instante': str,
}


def _ler_estado():
    """Carrega o estado da primeira origem, ou `None`.

    O arquivo atravessa máquinas, e JSON válido não quer dizer esquema
    válido: `backends_com_p1` vindo como inteiro fazia `set(...)` levantar
    `TypeError` FORA de todo caminho controlado — traceback e status 1, o
    mesmo de uma propriedade reprovada. Achado de revisão.
    """
    caminho = _caminho_do_estado()
    try:
        dados = json.loads(caminho.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        # `UnicodeDecodeError` não é subclasse de `JSONDecodeError`: um byte
        # corrompido na transferência entre as duas máquinas saía como
        # traceback com status 1 — o mesmo de propriedade reprovada. Arquivo
        # ilegível é estado ausente, que já tem caminho controlado. Achado de
        # revisão. `ValueError` cobre o resto da família de decodificação.
        return None
    if not isinstance(dados, dict):
        return None
    for campo, tipo in ESQUEMA_DO_ESTADO.items():
        valor = dados.get(campo)
        if not isinstance(valor, tipo) or isinstance(valor, bool):
            return None
    # `p3` ser um dict não basta: faltando uma chave, ou com classificação
    # desconhecida, `_classe_conservadora` simplesmente ignora a observação da
    # primeira origem — e um `sentinela_sobrevive` de A vira silêncio no
    # veredito de B. O estado atravessa máquinas; conferir o conteúdo é a
    # mesma disciplina que já vale para os outros campos. Achado de revisão.
    p3 = dados.get('p3') or {}
    for chave in ('cf', 'tc'):
        if p3.get(chave) not in CLASSES_VALIDAS:
            return None
    if not all(isinstance(x, str) for x in dados['backends_com_p1']):
        return None
    if not all(isinstance(k, str) and isinstance(v, str)
               for k, v in dados['urls'].items()):
        return None
    try:
        bytes.fromhex(dados['sal'])
    except ValueError:
        return None
    return dados


def _idade_do_estado(estado) -> str:
    """Quanto tempo separa a primeira medição desta, em texto legível.

    Não expira nada: o prazo é decisão do autor. O que isto faz é tirar a
    idade da evidência da invisibilidade — sem ela, uma medição de semanas
    atrás fecha o contrato sem que o relatório diga isso. Achado de revisão.
    """
    bruto = str((estado or {}).get('instante') or '')
    if not bruto:
        return ''
    try:
        quando = datetime.datetime.fromisoformat(bruto)
    except ValueError:
        return ''
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=datetime.timezone.utc)
    segundos = int((datetime.datetime.now(datetime.timezone.utc) - quando)
                   .total_seconds())
    if segundos < 0:
        return 'um instante no FUTURO — relógio de uma das máquinas está errado'
    if segundos < 3600:
        return f'{segundos // 60} min'
    if segundos < 86400:
        return f'{segundos // 3600} h {(segundos % 3600) // 60} min'
    return f'{segundos // 86400} dia(s) e {(segundos % 86400) // 3600} h'


def _validar_anterior(estado, ip_anterior: str, origem: str, hops: int,
                      obrigatorios: list, urls: dict = None) -> tuple:
    """A segunda origem só conta se estiver LIGADA a uma primeira medida.

    Sem esta verificação, qualquer endereço válido diferente do candidato faria
    `candidato_bate_com_origem_alternativa` dar `False`, e uma máquina só
    produziria código 0 com `ORIGEM_A != ORIGEM_B` sem a origem A ter existido.
    """
    if not ip_anterior:
        return False, 'sem EPI_IDENT_IP_ANTERIOR'
    if estado is None:
        return False, (
            'não achei o estado da primeira origem. Rode a origem A primeiro e '
            f'leve {_caminho_do_estado()} para esta máquina'
        )
    if estado.get('versao') != VERSAO_DO_ESTADO:
        return False, 'estado da primeira origem em versão desconhecida'
    if str(estado.get('origem', '')).strip() == origem:
        return False, (
            f'o estado guardado também é da origem {origem!r} — duas execuções '
            'do mesmo lugar não são duas origens'
        )
    if estado.get('hops') != hops:
        return False, (
            f'a primeira origem foi medida com hops={estado.get("hops")} e esta '
            f'com hops={hops}: não são comparáveis'
        )
    faltando = sorted(set(obrigatorios) - set(estado.get('backends_com_p1') or []))
    if faltando:
        return False, (
            'a primeira origem não teve P1 verdadeiro em: ' + ', '.join(faltando)
        )
    if urls is not None:
        guardadas = estado.get('urls') or {}
        atuais = {nome: _normalizar_url(url) for nome, url in urls.items()}
        if guardadas != atuais:
            divergentes = sorted(
                nome for nome in set(guardadas) | set(atuais)
                if guardadas.get(nome) != atuais.get(nome)
            )
            return False, (
                'a primeira origem mediu outro endpoint em: '
                + ', '.join(divergentes) + ' — P1 de um serviço não sustenta '
                'P2 de outro'
            )

    sal = str(estado.get('sal', ''))
    esperado = str(estado.get('compromisso', ''))
    try:
        calculado = _compromisso(sal, ip_anterior)
    except ValueError:
        return False, 'estado da primeira origem corrompido'
    if not esperado or not calculado or calculado != esperado:
        return False, (
            'EPI_IDENT_IP_ANTERIOR não é o endereço medido na primeira origem '
            '— declarar não é medir'
        )
    return True, f'ligado à origem {estado.get("origem")!r}'


def _rotulo(valor) -> str:
    if valor is None:
        return 'n/a'
    if valor is True:
        return 'true'
    if valor is False:
        return 'FALSE'
    return str(valor)


def _relatar(alvo: Alvo, tem_anterior: bool) -> None:
    print()
    print(f'[{alvo.nome}] {alvo.url}')
    if not alvo.configurado:
        print('   não configurado — variáveis de ambiente ausentes')
        return
    if not alvo.alcancado:
        print(f'   NÃO ALCANÇADO — {alvo.motivo}')
        return
    if alvo.contradicao:
        print(f'   INCONSISTENTE — {alvo.motivo}')
        return

    print(f'   P1  identidade ................ {_rotulo(alvo.p1)}')
    print(f'       contaminação do teste ..... {_rotulo(alvo.p1_contaminado)}')
    if tem_anterior:
        print(f'   P2  bate com a origem anterior  {_rotulo(alvo.p2_alt)}'
              '   (precisa ser FALSE)')
        print(f'       ligado à origem A medida .. {_rotulo(alvo.anterior_ligado)}'
              '   (precisa ser true)')
    else:
        print('   P2  segunda origem ............ n/a nesta execução')
    print(f'   P3  CF-Connecting-IP .......... {_rotulo(alvo.p3_cf)}')
    print(f'   P3  True-Client-IP ............ {_rotulo(alvo.p3_tc)}')
    print(f'   P4  sufixo preservado ......... {_rotulo(alvo.p4)}')
    # A varredura é o que separa "preservou naquela amostra" de "preserva em
    # produção": sem o tamanho, o veredito de P4 não diz até onde vale.
    detalhe = f'até {alvo.p4_maior_testado} elementos'
    if alvo.p4_quebrou_em:
        detalhe = f'QUEBROU em {alvo.p4_quebrou_em} elementos'
    elif alvo.p4_nao_chegou_em:
        detalhe = (f'NÃO CHEGOU: em {alvo.p4_nao_chegou_em} elementos a cadeia '
                   'recebida não cresceu — a borda filtra o que foi enviado, '
                   'e a amostra não testa nada')
    elif alvo.p4_ambigua_em:
        detalhe = (f'INCONCLUSIVO: recusa genérica em {alvo.p4_ambigua_em} '
                   'elementos não prova limite de TAMANHO')
    elif alvo.p4_recusada_em:
        detalhe += f'; a borda RECUSOU {alvo.p4_recusada_em} (fronteira)'
    else:
        # Sem recusa até o teto: a faixa testada não tem topo provado, e P4 não
        # é aprovado — é INCONCLUSIVO. Dizer só "até N" esconderia isso.
        detalhe += (' — INCONCLUSIVO: nenhuma fronteira foi encontrada, então '
                    'nada prova o comportamento acima deste tamanho')
    print(f'       cadeia do cliente ......... {detalhe}')
    print(f'       candidato é do cliente .... {_rotulo(alvo.candidato_do_cliente)}'
          '   (precisa ser FALSE)')
    # As duas linhas do LIMITADOR: o que foi medido é o que ele vai usar?
    print(f'   LIM X-Forwarded-For repetido .. {_rotulo(alvo.xff_duplicado)}'
          '   (precisa ser FALSE)')
    print(f'       candidato já canônico ..... {_rotulo(alvo.candidato_canonico)}'
          '   (precisa ser true)')


def _veredito(alvo: Alvo, tem_anterior: bool) -> tuple:
    """Devolve (satisfeito, pendente, motivo)."""
    if not alvo.alcancado or alvo.contradicao:
        return False, False, alvo.motivo or 'não medido'
    if alvo.p1_contaminado:
        return False, False, 'P1 contaminado: o candidato pode ter vindo do chamador'
    # As duas condições abaixo são sobre o LIMITADOR, não sobre a cadeia: elas
    # dizem que o que foi medido não é o que `core/rate_limit.py` vai usar.
    # Certificar assim mesmo seria licenciar `HOPS=3` para uma função
    # diferente da que se mediu. Achado de revisão.
    if alvo.xff_duplicado is not False:
        return False, False, (
            'X-Forwarded-For chegou em MAIS DE UMA instância: o limitador lê '
            'só a primeira (`headers.get`), e a borda pode ter posto a cadeia '
            'confiável noutra — `cadeia[-N]` sairia de dado do cliente'
        )
    if alvo.candidato_canonico is not True:
        return False, False, (
            'a borda não escreve o candidato em forma canônica, e o limitador '
            'usa a string CRUA como chave de balde: duas grafias do mesmo '
            'endereço ocupariam baldes diferentes'
        )
    if alvo.p1 is not True:
        return False, False, 'P1 falso: o candidato não é o endereço declarado'
    if alvo.candidato_do_cliente is not False:
        return False, False, 'o elemento selecionado veio do cliente'
    if alvo.p4 is not True:
        # DOIS desfechos diferentes moram em `p4 is not True`, e dizer "não
        # sobreviveu" nos dois mente num deles: quando a escada chega ao topo
        # sem recusa, o sufixo sobreviveu em TODOS os tamanhos medidos — o que
        # falta é FRONTEIRA. O operador que lê "não sobreviveu" vai procurar
        # uma borda que trunca e não vai achar nada. Achado da 13ª rodada,
        # consequência de tornar a ausência de fronteira reprovável.
        if (alvo.p4_quebrou_em is None and alvo.p4_ambigua_em is None
                and alvo.p4_nao_chegou_em is None and alvo.p4_recusada_em is None):
            return False, False, (
                f'P4 INCONCLUSIVO: o sufixo sobreviveu até {alvo.p4_maior_testado} '
                f'elementos e a borda não recusou nenhum tamanho — sem fronteira, '
                f'nada mediu o que acontece acima disso, e P4 vale para TODA '
                f'requisição que a aplicação aceita'
            )
        return False, False, 'P4 falso: a janela confiável não sobreviveu à cadeia longa'
    if not tem_anterior:
        return False, True, 'falta a segunda origem'
    if alvo.anterior_ligado is not True:
        return False, False, (
            'P2 sem lastro: o endereço declarado como origem anterior não foi '
            'medido na primeira execução'
        )
    if alvo.p2_alt is not False:
        return False, False, (
            'P2 falso: o candidato nesta origem é o endereço da origem anterior '
            '— as duas não são origens distintas'
        )
    return True, False, 'P1, P2 e P4 satisfeitos'


def main() -> int:
    bruto_hops = os.environ.get('EPI_IDENT_HOPS', '3').strip() or '3'
    try:
        hops = int(bruto_hops)
    except ValueError:
        # Antes isto levantava ValueError cru: traceback, e o shell via o mesmo
        # status 1 de uma propriedade REPROVADA. Um erro de digitação não pode
        # ser confundido com evidência de produção.
        print('PARE: EPI_IDENT_HOPS precisa ser inteiro.')
        return 2
    if hops < 1:
        print('PARE: EPI_IDENT_HOPS precisa ser >= 1.')
        return 2

    origem = os.environ.get('EPI_IDENT_ORIGEM', '').strip()
    meu_ip = os.environ.get('EPI_IDENT_MEU_IP', '').strip()
    ip_anterior = os.environ.get('EPI_IDENT_IP_ANTERIOR', '').strip()

    alvos = [
        Alvo('corporativo', os.environ.get('EPI_IDENT_CORP_URL', '').strip(),
             os.environ.get('EPI_IDENT_CORP_KEY', '').strip()),
        Alvo('saas', os.environ.get('EPI_IDENT_SAAS_URL', '').strip(),
             os.environ.get('EPI_IDENT_SAAS_KEY', '').strip()),
        Alvo('alternativo (investigação)', os.environ.get('EPI_IDENT_ALT_URL', '').strip(),
             os.environ.get('EPI_IDENT_ALT_KEY', '').strip()),
    ]
    obrigatorios = alvos[:2]
    alt = alvos[2]

    print('=' * 72)
    print('R0.5B — CERTIFICAÇÃO DA IDENTIDADE DA ORIGEM')
    print('=' * 72)
    print(f'origem declarada: {origem or "(sem rótulo)"}   ·   hops avaliado: {hops}')

    if not origem:
        print()
        print('PARE: defina EPI_IDENT_ORIGEM. Sem rótulo não há como dizer que')
        print('duas execuções vieram de caminhos diferentes.')
        return 2
    if not meu_ip:
        print()
        print('PARE: defina EPI_IDENT_MEU_IP com o endereço público desta máquina.')
        print('Ele é enviado à sonda para comparação e NUNCA é impresso aqui.')
        return 2
    if not _canonico(meu_ip):
        print()
        print('PARE: EPI_IDENT_MEU_IP não é um endereço IP válido.')
        return 2
    if not _origem_plausivel(meu_ip):
        print()
        print('PARE: EPI_IDENT_MEU_IP não é um endereço público.')
        print('Privado, loopback, CGNAT ou multicast não é origem pública, e o')
        print('contrato exige duas origens PÚBLICAS distintas.')
        return 2
    if ip_anterior and not _origem_plausivel(ip_anterior):
        print()
        print('PARE: EPI_IDENT_IP_ANTERIOR não é um endereço público.')
        return 2

    # Os DOIS backends, sempre. Antes, configurar só um deixava `obrigatorios`
    # com um alvo, todas as conferências passavam, e o script anunciava "nos
    # dois backends". Uma variável esquecida tirava um deployment inteiro da
    # certificação em silêncio.
    faltando = [a.nome for a in obrigatorios if not a.configurado]
    if faltando:
        print()
        print('PARE: faltam URL e/ou chave de: ' + ', '.join(faltando) + '.')
        print('A certificação vale para os DOIS backends onde HOPS será')
        print('aplicado, ou não vale. Não há meia certificação.')
        return 2

    # O alternativo entra aqui quando CONFIGURADO: com URL malformada ele
    # cairia em "não comprovado — não alcançou o serviço", que é conclusão
    # sobre o mundo, quando o que houve foi erro de digitação. Mesma razão do
    # `pela metade` logo abaixo: o operador pediu para investigar.
    malformadas = [a.nome for a in alvos if a.configurado and not _normalizar_url(a.url)]
    if malformadas:
        print()
        print('PARE: URL inválida em: ' + ', '.join(malformadas) + '.')
        return 2

    distintas = {_normalizar_url(a.url) for a in obrigatorios}
    if len(distintas) != len(obrigatorios):
        print()
        print('PARE: EPI_IDENT_CORP_URL e EPI_IDENT_SAAS_URL apontam para o')
        print('MESMO endpoint. Um deployment não certifica dois: a comparação')
        print('entre backends viraria a mesma medição consigo mesma.')
        return 2

    # URL sem chave (ou o contrário) não é "não investigado": é o operador
    # pedindo para investigar e o alvo sendo pulado em silêncio.
    if bool(alt.url) != bool(alt.chave):
        print()
        print('PARE: o hostname alternativo está configurado pela metade.')
        print('Defina EPI_IDENT_ALT_URL e EPI_IDENT_ALT_KEY, ou nenhum dos dois.')
        return 2

    urls_atuais = {a.nome: a.url for a in obrigatorios}
    estado = _ler_estado() if ip_anterior else None
    nomes_obrigatorios = [a.nome for a in obrigatorios]
    ligado, motivo_do_vinculo = (False, 'primeira origem')
    if ip_anterior:
        ligado, motivo_do_vinculo = _validar_anterior(
            estado, ip_anterior, origem, hops, nomes_obrigatorios, urls_atuais)

    tem_anterior = bool(ip_anterior)
    for alvo in alvos:
        if alvo.configurado:
            medir(alvo, hops, meu_ip, ip_anterior)
        if alvo is not alt:
            alvo.anterior_ligado = ligado if tem_anterior else None
        _relatar(alvo, tem_anterior)

    print()
    print('=' * 72)
    if tem_anterior:
        print(f'vínculo com a primeira origem: {"OK" if ligado else "AUSENTE"}'
              f' — {motivo_do_vinculo}')
        print()

    # Alvo inalcançável é AUSÊNCIA de medição, não medição que reprovou. O
    # veredito devolvia (False, False) para os dois casos e `main` respondia 1,
    # então automação não distinguia "a sonda não respondeu" de "a produção
    # rejeitou a propriedade". Contradição é outra coisa: foi medido, e as
    # medições se contradizem — isso continua sendo 1.
    inalcancados = [a for a in obrigatorios if not a.alcancado]
    if inalcancados:
        print('RESULTADO: não executado — backend inalcançável:')
        for alvo in inalcancados:
            print(f'   {alvo.nome}: {alvo.motivo}')
        print('Isto NÃO é evidência sobre nenhuma propriedade.')
        return 2

    veredito = [(_veredito(a, tem_anterior), a) for a in obrigatorios]

    for (ok, pendente, motivo), alvo in veredito:
        estado_txt = 'OK' if ok else ('PENDENTE' if pendente else 'REPROVADO')
        print(f'{alvo.nome:14} {estado_txt:10} {motivo}')

    # P3 é classificação, não critério de HOPS. Mas um sentinela que SOBREVIVE
    # significa que o cliente controla o cabeçalho, e isso não pode sair
    # diluído no meio de um "tudo certo".
    # TODA rota alcançada entra no resumo, não só as obrigatórias. Um
    # alternativo que RESPONDE é uma entrada pública de verdade: se o cliente
    # controla o cabeçalho lá, o resumo não pode terminar com "nenhum
    # cabeçalho sobreviveu" — o operador fecharia o contrato adotando um
    # cabeçalho que a seção por alvo já mostrou controlado. Achado de revisão.
    alcancadas = [a for a in alvos if a.alcancado and not a.contradicao]
    p3_desta_origem = {
        'cf': _classe_conservadora(*[a.p3_cf for a in alcancadas]),
        'tc': _classe_conservadora(*[a.p3_tc for a in alcancadas]),
    }
    # E o que a PRIMEIRA origem observou. Sobreviver em QUALQUER uma das duas
    # execuções torna o cabeçalho não adotável: o tratamento pode variar por
    # rota, e sem isto o resultado de A sumia do relatório final — o operador
    # fecharia o contrato com a classificação de B só. Achado de revisão.
    p3_anterior = (estado.get('p3') or {}) if (ligado and estado) else {}
    p3_final = {chave: _classe_conservadora(p3_desta_origem.get(chave),
                                            p3_anterior.get(chave))
                for chave in ('cf', 'tc')}
    controlados = sorted(
        nome for chave, nome in (('cf', 'CF-Connecting-IP'),
                                 ('tc', 'True-Client-IP'))
        if p3_final.get(chave) == 'sentinela_sobrevive'
    )
    print()
    if p3_anterior:
        print(f'P3 da primeira origem: CF-Connecting-IP='
              f'{p3_anterior.get("cf") or "?"}, '
              f'True-Client-IP={p3_anterior.get("tc") or "?"}')
        print('   A classificação que vale é a das DUAS origens juntas.')
    if controlados:
        print('ALERTA P3: o cliente CONTROLA ' + ', '.join(controlados) + '.')
        print('   Esses cabeçalhos não são adotáveis como fonte de identidade,')
        print('   em rota nenhuma. Não reprova HOPS — é achado próprio, e grave.')
    else:
        print('P3: nenhum cabeçalho de identidade sobreviveu ao sentinela.')
        print('   Medido com sentinela de documentação E de CGNAT. Uma borda')
        print('   que higienize tudo que não é global e ainda assim repasse')
        print('   valor de forma pública não é separada por este controle —')
        print('   limitação registrada no §7 do contrato.')

    # O hostname alternativo entra como evidência, nunca como equivalência.
    print()
    if not alt.configurado:
        print('hostname alternativo: não investigado nesta execução')
    elif alt.contradicao:
        # Responder E se contradizer entre repetições é evidência de MAIS DE UM
        # caminho de borda numa entrada pública. Isso ataca a cobertura de
        # rota, que é premissa do critério — não pode ser informativo.
        print('hostname alternativo: RESPONDE e se CONTRADIZ entre repetições')
        print(f'   {alt.motivo}')
        print('   Entrada pública com mais de um caminho de borda derruba a')
        print('   premissa de rota do critério.')
        print()
        print('RESULTADO: cobertura de rota REPROVADA. HOPS permanece')
        print('PARCIALMENTE PROVADO e RATE_LIMIT_TRUSTED_PROXY_HOPS permanece 0.')
        return 1
    elif alt.alcancado:
        print('hostname alternativo: RESPONDE a sonda R0.5B — é uma entrada '
              'pública adicional e entra na matriz')
        # Responder e REPROVAR de forma estável é pior que se contradizer: é
        # uma entrada pública onde a janela `N` não vale. A primeira versão só
        # reprovava a contradição e deixava o negativo estável passar como
        # informativo. Achado de revisão.
        # `tem_anterior=False` de propósito: o estado da primeira origem NÃO
        # guarda evidência para o alternativo, então P2 nunca está estabelecido
        # aqui. Com `False`, o veredito devolve PENDENTE quando tudo o mais
        # passa — o alternativo serve para REJEITAR, nunca para certificar.
        # Emprestar o `ligado` dos obrigatórios deixaria uma rota adicional
        # passar por coberta sem medição nenhuma na origem A.
        ok_alt, pendente_alt, motivo_alt = _veredito(alt, False)
        if not ok_alt and not pendente_alt:
            print(f'   mas REPROVA: {motivo_alt}')
            print('   Uma entrada pública onde a janela não vale derruba a')
            print('   premissa de rota do critério.')
            print()
            print('RESULTADO: cobertura de rota REPROVADA. HOPS permanece')
            print('PARCIALMENTE PROVADO e RATE_LIMIT_TRUSTED_PROXY_HOPS '
                  'permanece 0.')
            return 1
    else:
        print(f'hostname alternativo: não comprovado — {alt.motivo}')

    if ligado and estado:
        idade = _idade_do_estado(estado)
        if idade:
            print()
            print(f'Evidência da primeira origem gravada há {idade}.')
            print('   O script NÃO expira o compromisso: se o deployment ou a')
            print('   topologia mudaram entre as duas medições, elas não são')
            print('   comparáveis, e só você sabe se mudaram.')

    print()
    if any(not ok and not pendente for (ok, pendente, _), _ in veredito):
        print('RESULTADO: propriedade REPROVADA. HOPS permanece PARCIALMENTE')
        print('PROVADO e RATE_LIMIT_TRUSTED_PROXY_HOPS permanece 0.')
        return 1
    if any(pendente for (ok, pendente, _), _ in veredito):
        limpos = [a.nome for a in obrigatorios
                  if a.p1 is True and a.p1_contaminado is False
                  and a.candidato_do_cliente is False]
        try:
            caminho = _gravar_estado(origem, hops, meu_ip, limpos,
                                     urls_atuais, p3_desta_origem)
        except OSError as e:
            # Sem o compromisso gravado, a segunda origem não tem como se ligar
            # à primeira. A medição aconteceu, mas a cadeia A→B não pode
            # prosseguir — isso é "não executado", não "propriedade reprovada".
            # Sem este tratamento saía traceback com status 1, o mesmo de uma
            # propriedade rejeitada. Achado de revisão.
            print(f'PARE: não consegui gravar o compromisso em '
                  f'{_caminho_do_estado()}: {e}')
            print('Sem ele a segunda origem não tem como se ligar a esta.')
            print('Aponte EPI_IDENT_ESTADO para um caminho gravável e repita.')
            return 2
        print(f'RESULTADO: medido na origem {origem!r}, falta a SEGUNDA origem.')
        print(f'Compromisso gravado em {caminho} — LOCAL, não vai em commit,')
        print('não sai no relatório. Leve-o se a segunda origem for outra máquina.')
        print('Lá, defina EPI_IDENT_IP_ANTERIOR com o endereço público DESTA.')
        # A segunda execução só apaga a cópia que ela enxerga. Dizer "leve" e
        # deixar o operador COPIAR guarda uma evidência de primeira origem
        # viva aqui, reutilizável quando a topologia já mudou. Achado de
        # revisão; o script não alcança outra máquina, então o que ele pode
        # fazer é dizer a verdade e mandar mover.
        print()
        print('MOVA o arquivo, não copie. A segunda execução só consegue apagar')
        print('a cópia que estiver na máquina dela; uma cópia esquecida aqui')
        print('continua valendo como evidência de primeira origem depois.')
        return 3

    # P3 fica FORA da concordância: ele é classificação, não critério de HOPS,
    # e o próprio roteiro diz isso. Duas bordas podem classificar um cabeçalho
    # de identidade de formas diferentes de maneira legítima — `substituida`
    # num lado e `ausente` no outro — e reprovar a certificação por causa disso
    # contradizia o contrato documentado. Achado de revisão.
    resultados = {(a.p1, a.p2_alt, a.p4) for a in obrigatorios}
    if len(resultados) > 1:
        print('RESULTADO: os dois backends NÃO concordam em P1/P2/P4. Cada um')
        print('precisa da sua própria conclusão — não unifique.')
        return 1

    classes = {(a.p3_cf, a.p3_tc) for a in obrigatorios}
    if len(classes) > 1:
        print('NOTA: os backends classificam os cabeçalhos de identidade de')
        print('formas diferentes. Não reprova HOPS — P3 não é critério —, mas')
        print('cada borda precisa da sua própria conclusão sobre adotá-los.')
        print()

    # O compromisso sai de cena junto com a certificação. Deixá-lo guardaria o
    # sal e o compromisso do endereço público indefinidamente — e, pior, ele
    # continuaria REUTILIZÁVEL como evidência de primeira origem em execuções
    # posteriores, quando o deployment ou a topologia já podem ter mudado.
    # Achado de revisão.
    try:
        _caminho_do_estado().unlink()
        print(f'Compromisso apagado AQUI ({_caminho_do_estado()}): a certificação')
        print('fechou. Se a primeira origem foi outra máquina e você COPIOU o')
        print('arquivo em vez de mover, apague a cópia de lá: esta execução não')
        print('alcança nada fora desta máquina, e aquela cópia continua valendo.')
    except FileNotFoundError:
        # Já não existe: é o estado desejado, não um erro. Acontece quando a
        # certificação roda duas vezes, ou quando a origem A e a B são a mesma
        # máquina e o arquivo já saiu na primeira passagem.
        pass
    except OSError as e:
        # Sair 0 aqui declararia a certificação fechada deixando o compromisso
        # REUTILIZÁVEL como evidência de primeira origem numa execução futura,
        # quando a topologia já pode ter mudado. As propriedades passaram, mas
        # o encerramento não — e são coisas distintas. Achado de revisão.
        print(f'PARE: não consegui apagar {_caminho_do_estado()}: {e}')
        print()
        print('As propriedades P1, P2 e P4 foram satisfeitas, mas o')
        print('encerramento NÃO fechou: o compromisso continua no disco e')
        print('continua reutilizável como evidência de primeira origem.')
        print('Apague-o à mão e repita a segunda origem.')
        return 4
    print()

    print('RESULTADO: P1, P2 e P4 satisfeitos nos dois backends.')
    print(f'   ORIGEM_A != ORIGEM_B: true   (origem desta execução: {origem!r})')
    print('   Isto cobre identidade. Cobertura de rota continua sendo pergunta')
    print('   separada — ver docs/R05B_IDENTIDADE_DA_ORIGEM.md §3.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
