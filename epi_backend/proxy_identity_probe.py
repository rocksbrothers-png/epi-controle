"""R0.5B — sonda TEMPORÁRIA de identidade da origem.

Responde UMA pergunta: qual elemento da cadeia recebida corresponde à origem
pública real do chamador, e essa posição é estável entre duas origens
distintas?

Nunca devolve endereço — nem o peer, nem elementos da cadeia, nem a
reivindicação enviada. Só booleanos e contagens. O operador compara; a sonda
não certifica.

`candidato_bate_com_origem_declarada` é um oráculo de igualdade: quem tem a
chave testa endereços um a um. Aceito deliberadamente — a chave é do operador
e a sonda sai do repositório quando a medição fechar. Devolver o endereço
transformaria um oráculo lento em vazamento direto.

Sem `PROXY_CHAIN_PROBE_KEY` no ambiente a rota devolve 404, como se não
existisse.
"""

from __future__ import annotations

import hmac
import ipaddress
import os

#: TEST-NET-1 (RFC 5737): espaço de documentação que nenhuma infraestrutura
#: real emite. Se chega à aplicação, veio do cliente — é isso que o torna
#: sentinela, e é como se distingue o que a borda escreveu do que o cliente
#: enviou.
REDE_SENTINELA = ipaddress.ip_network('192.0.2.0/24')

CABECALHO_CHAVE = 'X-Diagnostics-Key'
CABECALHO_HOPS = 'X-Probe-Hops'
CABECALHO_REIVINDICACAO = 'X-Origin-Claim'
HOPS_MAXIMO = 16

#: Declarado aqui, onde é lido: o nome sai do repositório junto com a sonda.
NOME_DA_VARIAVEL = 'PROXY_CHAIN_PROBE_KEY'


def _cabecalho(handler, nome: str) -> str:
    """Todas as instâncias, juntadas por vírgula — a semântica de HTTP."""
    try:
        valores = handler.headers.get_all(nome) or []
    except Exception:
        valores = []
    return ', '.join(str(v).strip() for v in valores if str(v).strip())


def _como_o_limitador(handler, nome: str) -> str:
    """Só a PRIMEIRA instância: é o que `core/rate_limit.py` lê."""
    try:
        return str(handler.headers.get(nome, '') or '').strip()
    except Exception:
        return ''


def _normalizar(valor: str) -> str:
    """Forma canônica do endereço; '' se não for endereço."""
    try:
        endereco = ipaddress.ip_address(str(valor).strip())
    except ValueError:
        return ''
    if endereco.version == 6 and endereco.ipv4_mapped is not None:
        endereco = endereco.ipv4_mapped
    return str(endereco)


def _e_sentinela(valor: str) -> bool:
    canonico = _normalizar(valor)
    if not canonico:
        return False
    try:
        return ipaddress.ip_address(canonico) in REDE_SENTINELA
    except ValueError:
        return False


def analisar(cadeia: list, hops: int, reivindicacao: str,
             *, instancias_repetidas: bool = False) -> dict:
    """Avalia a cadeia já extraída. Nunca devolve endereço."""
    tamanho = len(cadeia)
    suficiente = hops >= 1 and tamanho >= hops
    i = tamanho - hops if suficiente else None
    candidato = _normalizar(cadeia[i]) if suficiente else ''
    alvo = _normalizar(reivindicacao)
    return {
        'probe': 'R05B',
        'hops_avaliado': hops,
        'cadeia_tamanho': tamanho,
        'cadeia_suficiente_para_hops': suficiente,
        # O candidato é o endereço que o chamador diz ser o seu?
        'candidato_bate_com_origem_declarada': (
            hmac.compare_digest(candidato.encode(), alvo.encode())
            if alvo and suficiente else None
        ),
        # O candidato saiu do prefixo que o CLIENTE enviou? Se sim, `hops` está
        # errado e a seleção cairia em dado escolhido pelo chamador.
        'candidato_e_do_cliente': suficiente and _e_sentinela(cadeia[i]),
        'prefixo_do_cliente_presente': any(_e_sentinela(e) for e in cadeia),
        # Mais de uma instância de X-Forwarded-For: o limitador lê só a
        # primeira (`headers.get`), então mediríamos uma coisa e ele usaria
        # outra. Ver a classificação de D em docs/R05B_IDENTIDADE_DA_ORIGEM.md.
        'xff_instancias_repetidas': bool(instancias_repetidas),
        # O limitador usa a string CRUA como chave de balde. Se a borda não
        # escreve a forma canônica, duas grafias do mesmo endereço ocupam
        # baldes diferentes. Classificação de E no mesmo documento.
        'candidato_ja_canonico': (
            not suficiente
            or cadeia[i].strip() == _normalizar(cadeia[i])
        ),
    }


def chave_configurada() -> str:
    return str(os.environ.get(NOME_DA_VARIAVEL, '')).strip()


def autorizado(handler) -> bool:
    chave = chave_configurada()
    if not chave:
        return False
    # Compara BYTES: com `str`, `compare_digest` levanta TypeError em caractere
    # fora de ASCII, e o 500 distinguiria rota protegida de rota ausente.
    return hmac.compare_digest(
        _como_o_limitador(handler, CABECALHO_CHAVE).encode('utf-8'),
        chave.encode('utf-8'),
    )


def medir(handler) -> dict:
    bruto = _como_o_limitador(handler, 'X-Forwarded-For')
    try:
        hops = int(_como_o_limitador(handler, CABECALHO_HOPS) or '0')
    except ValueError:
        hops = 0
    return analisar(
        [p.strip() for p in bruto.split(',') if p.strip()],
        max(0, min(hops, HOPS_MAXIMO)),
        _como_o_limitador(handler, CABECALHO_REIVINDICACAO),
        instancias_repetidas=_cabecalho(handler, 'X-Forwarded-For') != bruto,
    )
