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
`sha256(sal || endereço)`, com sal aleatório — e só o grava se P1 tiver sido
verdadeiro ali. A segunda execução recalcula o compromisso a partir do que você
declarou em `EPI_IDENT_IP_ANTERIOR` e exige que bata.

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
segunda.

P3 **não** entra no veredito: ele classifica cabeçalhos, e a classificação é
reportada à parte. Um `sentinela_sobrevive` não reprova `HOPS`, mas é achado
grave por conta própria — o relatório o destaca.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROTA = '/api/origin-identity-diagnostics'
TIMEOUT = 30
REPETICOES = 3

# TEST-NET-1 (RFC 5737): documentação, não roteável, nunca emitido por
# infraestrutura real. Serve de sentinela justamente por isso.
SENTINELA_CF = '192.0.2.10'
SENTINELA_TC = '192.0.2.11'
CADEIA_LONGA = ', '.join(f'192.0.2.{n}' for n in range(20, 50))  # 30 elementos

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
    'cf_connecting_ip',
    'true_client_ip',
)

#: A sonda promete escalares. Um campo que chegue como lista ou dicionário
#: rebentaria a construção do conjunto de formas com `TypeError`, FORA dos
#: caminhos controlados — o operador veria traceback em vez de código de saída.
TIPOS_ESCALARES = (bool, int, float, str, type(None))

#: Estado que liga a segunda origem à primeira. Fica FORA do repositório de
#: propósito: não entra em commit por acidente, e o gate que varre endereços
#: reais nas superfícies da fatia continua valendo.
ESTADO_PADRAO = Path.home() / '.r05b_origem_anterior.json'
VERSAO_DO_ESTADO = 1


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


def _forma(nome: str, amostra: dict) -> tuple:
    """Chave de comparação entre repetições, com os tipos conferidos.

    Uma sonda de versão diferente pode devolver o marcador certo e um campo
    decisivo malformado. Sem esta conferência, `{...}` levantaria `TypeError:
    unhashable type` fora de `NaoAlcancado`/`Inconsistente`, e o operador
    receberia traceback em vez de um dos códigos documentados.
    """
    valores = []
    for campo in CAMPOS_DECISIVOS:
        valor = amostra.get(campo)
        if not isinstance(valor, TIPOS_ESCALARES):
            raise NaoAlcancado(
                f'controle {nome}: o campo {campo!r} veio como '
                f'{type(valor).__name__}, não escalar — a resposta não segue o '
                'contrato da sonda R0.5B'
            )
        valores.append(valor)
    return tuple(valores)


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


def _compromisso(sal_hex: str, endereco: str) -> str:
    """`sha256(sal || endereço canônico)`.

    O sal existe porque o espaço IPv4 tem 2^32 elementos: um digesto sem sal
    seria consulta de tabela. Com sal, o arquivo continua local e nunca sai no
    relatório — o relatório diz apenas se bateu.
    """
    canonico = _canonico(endereco)
    if not canonico:
        return ''
    return hashlib.sha256(bytes.fromhex(sal_hex) + canonico.encode('utf-8')).hexdigest()


def _controle(nome: str, **kwargs) -> dict:
    """Repete a mesma sondagem e exige que as repetições concordem.

    A R0.5 aprendeu isso da pior forma: uma requisição só não distingue medição
    de coincidência.
    """
    amostras = [_sondar(**kwargs) for _ in range(REPETICOES)]
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


def _caminho_do_estado() -> Path:
    bruto = os.environ.get('EPI_IDENT_ESTADO', '').strip()
    return Path(bruto) if bruto else ESTADO_PADRAO


def _gravar_estado(origem: str, hops: int, meu_ip: str, nomes_ok: list) -> Path:
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
    }, indent=2), encoding='utf-8')
    return caminho


def _ler_estado():
    caminho = _caminho_do_estado()
    try:
        dados = json.loads(caminho.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    return dados if isinstance(dados, dict) else None


def _validar_anterior(estado, ip_anterior: str, origem: str, hops: int,
                      obrigatorios: list) -> tuple:
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

    estado = _ler_estado() if ip_anterior else None
    nomes_obrigatorios = [a.nome for a in obrigatorios]
    ligado, motivo_do_vinculo = (False, 'primeira origem')
    if ip_anterior:
        ligado, motivo_do_vinculo = _validar_anterior(
            estado, ip_anterior, origem, hops, nomes_obrigatorios)

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

    veredito = [(_veredito(a, tem_anterior), a) for a in obrigatorios]

    for (ok, pendente, motivo), alvo in veredito:
        estado_txt = 'OK' if ok else ('PENDENTE' if pendente else 'REPROVADO')
        print(f'{alvo.nome:14} {estado_txt:10} {motivo}')

    # P3 é classificação, não critério de HOPS. Mas um sentinela que SOBREVIVE
    # significa que o cliente controla o cabeçalho, e isso não pode sair
    # diluído no meio de um "tudo certo".
    controlados = sorted({
        nome
        for alvo in obrigatorios
        for nome, classe in (('CF-Connecting-IP', alvo.p3_cf),
                             ('True-Client-IP', alvo.p3_tc))
        if classe == 'sentinela_sobrevive'
    })
    print()
    if controlados:
        print('ALERTA P3: o cliente CONTROLA ' + ', '.join(controlados) + '.')
        print('   Esses cabeçalhos não são adotáveis como fonte de identidade,')
        print('   em rota nenhuma. Não reprova HOPS — é achado próprio, e grave.')
    else:
        print('P3: nenhum cabeçalho de identidade sobreviveu ao sentinela.')

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
    else:
        print(f'hostname alternativo: não comprovado — {alt.motivo}')

    print()
    if any(not ok and not pendente for (ok, pendente, _), _ in veredito):
        print('RESULTADO: propriedade REPROVADA. HOPS permanece PARCIALMENTE')
        print('PROVADO e RATE_LIMIT_TRUSTED_PROXY_HOPS permanece 0.')
        return 1
    if any(pendente for (ok, pendente, _), _ in veredito):
        limpos = [a.nome for a in obrigatorios
                  if a.p1 is True and a.p1_contaminado is False
                  and a.candidato_do_cliente is False]
        caminho = _gravar_estado(origem, hops, meu_ip, limpos)
        print(f'RESULTADO: medido na origem {origem!r}, falta a SEGUNDA origem.')
        print(f'Compromisso gravado em {caminho} — LOCAL, não vai em commit,')
        print('não sai no relatório. Leve-o se a segunda origem for outra máquina.')
        print('Lá, defina EPI_IDENT_IP_ANTERIOR com o endereço público DESTA.')
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
