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

Saída: 0 = todas as propriedades satisfeitas · 1 = propriedade reprovada ou
medições contraditórias · 2 = não executado / alvo inalcançável · 3 = medido,
falta a segunda origem.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROTA = '/api/origin-identity-diagnostics'
TIMEOUT = 30
REPETICOES = 3

# TEST-NET-1 (RFC 5737): documentação, não roteável, nunca emitido por
# infraestrutura real. Serve de sentinela justamente por isso.
SENTINELA_CF = '192.0.2.10'
SENTINELA_TC = '192.0.2.11'
CADEIA_LONGA = ', '.join(f'192.0.2.{n}' for n in range(20, 50))  # 30 elementos

#: Campos cuja divergência entre repetições invalida a medição.
CAMPOS_DECISIVOS = (
    'cadeia_tamanho',
    'cadeia_suficiente_para_hops',
    'candidato_e_do_cliente',
    'sufixo_confiavel_preservado',
    'candidato_bate_com_origem_declarada',
    'candidato_bate_com_origem_alternativa',
    'cf_connecting_ip',
    'true_client_ip',
)


class NaoAlcancado(Exception):
    """Não deu para medir. Diferente de medir e reprovar."""


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


def _sondar(base_url: str, chave: str, hops: int, *, xff=None, cf=None,
            tc=None, reivindicacao='', alternativa='') -> dict:
    url = base_url.rstrip('/') + ROTA
    if not url.lower().startswith('https://'):
        raise NaoAlcancado('a URL precisa ser https — a chave viaja em cabeçalho')

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
            raise NaoAlcancado(
                'sonda desligada ou ausente (404) — o serviço precisa estar '
                'rodando a versão com a sonda E ter PROXY_CHAIN_PROBE_KEY'
            ) from e
        raise NaoAlcancado(f'HTTP {e.code} em {ROTA}') from e
    except json.JSONDecodeError as e:
        raise NaoAlcancado('resposta não é JSON — este host serve a API?') from e
    except NaoAlcancado:
        raise
    except Exception as e:  # noqa: BLE001 — rede é imprevisível; vira relatório
        raise NaoAlcancado(f'não alcançou o serviço: {e}') from e


def _controle(nome: str, **kwargs) -> dict:
    """Repete a mesma sondagem e exige que as repetições concordem.

    A R0.5 aprendeu isso da pior forma: uma requisição só não distingue medição
    de coincidência.
    """
    amostras = [_sondar(**kwargs) for _ in range(REPETICOES)]
    formas = {tuple(a.get(c) for c in CAMPOS_DECISIVOS) for a in amostras}
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
        self.p3_cf = None
        self.p3_tc = None
        self.p4 = None
        self.candidato_do_cliente = None

    @property
    def configurado(self) -> bool:
        return bool(self.url and self.chave)


def medir(alvo: Alvo, hops: int, meu_ip: str, ip_anterior: str) -> None:
    comum = dict(base_url=alvo.url, chave=alvo.chave, hops=hops)
    try:
        # P1 — SEM `X-Forwarded-For`. É essa ausência que garante que toda a
        # cadeia recebida foi escrita pela borda, e que a reivindicação não
        # pode ter sido usada para construir o candidato.
        identidade = _controle('P1 (identidade)', **comum,
                               reivindicacao=meu_ip, alternativa=ip_anterior)

        cf = _controle('P3 (CF-Connecting-IP)', **comum, cf=SENTINELA_CF)
        tc = _controle('P3 (True-Client-IP)', **comum, tc=SENTINELA_TC)
        longa = _controle('P4 (cadeia longa)', **comum, xff=CADEIA_LONGA)
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

    # Contaminação: os três guardas juntos. Se qualquer um disparar, P1 não é
    # evidência de nada — o candidato pode ter vindo do que o chamador enviou.
    alvo.p1_contaminado = bool(
        identidade.get('prefixo_do_cliente_presente')
        or identidade.get('cadeia_maior_que_hops')
        or identidade.get('reivindicacao_fora_do_candidato')
    )

    alvo.p3_cf = cf.get('cf_connecting_ip')
    alvo.p3_tc = tc.get('true_client_ip')
    alvo.p4 = bool(longa.get('sufixo_confiavel_preservado')
                   and not longa.get('candidato_e_do_cliente'))


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
    else:
        print('   P2  segunda origem ............ n/a nesta execução')
    print(f'   P3  CF-Connecting-IP .......... {_rotulo(alvo.p3_cf)}')
    print(f'   P3  True-Client-IP ............ {_rotulo(alvo.p3_tc)}')
    print(f'   P4  sufixo preservado ......... {_rotulo(alvo.p4)}')
    print(f'       candidato é do cliente .... {_rotulo(alvo.candidato_do_cliente)}'
          '   (precisa ser FALSE)')


def _veredito(alvo: Alvo, tem_anterior: bool) -> tuple:
    """Devolve (satisfeito, pendente, motivo)."""
    if not alvo.alcancado or alvo.contradicao:
        return False, False, alvo.motivo or 'não medido'
    if alvo.p1_contaminado:
        return False, False, 'P1 contaminado: o candidato pode ter vindo do chamador'
    if alvo.p1 is not True:
        return False, False, 'P1 falso: o candidato não é o endereço declarado'
    if alvo.candidato_do_cliente is not False:
        return False, False, 'o elemento selecionado veio do cliente'
    if alvo.p4 is not True:
        return False, False, 'P4 falso: a janela confiável não sobreviveu à cadeia longa'
    if not tem_anterior:
        return False, True, 'falta a segunda origem'
    if alvo.p2_alt is not False:
        return False, False, (
            'P2 falso: o candidato nesta origem é o endereço da origem anterior '
            '— as duas não são origens distintas'
        )
    return True, False, 'P1, P2 e P4 satisfeitos'


def main() -> int:
    hops = int(os.environ.get('EPI_IDENT_HOPS', '3') or 3)
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

    tem_anterior = bool(ip_anterior)
    for alvo in alvos:
        if alvo.configurado:
            medir(alvo, hops, meu_ip, ip_anterior)
        _relatar(alvo, tem_anterior)

    print()
    print('=' * 72)

    obrigatorios = [a for a in alvos if a.configurado and not a.nome.startswith('alternativo')]
    if not obrigatorios:
        print('RESULTADO: nenhum backend configurado — nada medido.')
        return 2

    veredito = [(_veredito(a, tem_anterior), a) for a in obrigatorios]

    for (ok, pendente, motivo), alvo in veredito:
        estado = 'OK' if ok else ('PENDENTE' if pendente else 'REPROVADO')
        print(f'{alvo.nome:14} {estado:10} {motivo}')

    # O hostname alternativo entra como evidência, nunca como equivalência.
    alt = alvos[2]
    print()
    if not alt.configurado:
        print('hostname alternativo: não investigado nesta execução')
    elif alt.alcancado:
        print('hostname alternativo: RESPONDE a sonda R0.5B — é uma entrada '
              'pública adicional e entra na matriz')
    else:
        print(f'hostname alternativo: não comprovado — {alt.motivo}')

    print()
    if any(not ok and not pendente for (ok, pendente, _), _ in veredito):
        print('RESULTADO: propriedade REPROVADA. HOPS permanece PARCIALMENTE')
        print('PROVADO e RATE_LIMIT_TRUSTED_PROXY_HOPS permanece 0.')
        return 1
    if any(pendente for (ok, pendente, _), _ in veredito):
        print(f'RESULTADO: medido na origem {origem!r}, falta a SEGUNDA origem.')
        print('Repita de uma rede independente, com EPI_IDENT_IP_ANTERIOR')
        print('apontando para o endereço público desta primeira.')
        return 3

    resultados = {(a.p1, a.p2_alt, a.p3_cf, a.p3_tc, a.p4) for a in obrigatorios}
    if len(resultados) > 1:
        print('RESULTADO: os dois backends NÃO concordam. Cada um precisa da')
        print('sua própria conclusão — não unifique.')
        return 1

    print('RESULTADO: P1, P2 e P4 satisfeitos nos dois backends.')
    print(f'   ORIGEM_A != ORIGEM_B: true   (origem desta execução: {origem!r})')
    print('   Isto cobre identidade. Cobertura de rota continua sendo pergunta')
    print('   separada — ver docs/R05B_IDENTIDADE_DA_ORIGEM.md §3.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
