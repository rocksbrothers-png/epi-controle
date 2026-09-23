"""R0.5B — sonda TEMPORÁRIA de identidade da origem.

## Por que existe uma sonda nova

A R0.5 mediu a **forma** da cadeia: a borda contribui com 3 elementos, e essa
contribuição não varia com o que o cliente envia. Isso refutou spoofing na rota
medida e não provou mais nada.

O que ficou sem observação é a **identidade**: que o elemento escolhido por
`cadeia[-N]` represente quem originou a requisição. A sonda anterior não podia
responder isso por construção — ela devolvia só contagens e posições, nunca
comparava nada com endereço nenhum.

Esta sonda existe para responder quatro propriedades, e só elas:

    P1  o elemento em `cadeia[-N]` é o endereço que o próprio chamador
        observa como sendo o seu?
    P2  isso vale a partir de duas origens públicas realmente distintas?
    P3  `CF-Connecting-IP` e `True-Client-IP` são escritos pela borda, ou o
        cliente consegue controlá-los?
    P4  uma cadeia longa enviada pelo cliente desloca ou trunca o sufixo que
        `cadeia[-N]` pretende usar?

Ela **não** reaproveita o desenho anterior: outra rota, outro módulo, outro
esquema de resposta.

## O que ela nunca devolve

Endereço nenhum — nem o peer, nem elementos da cadeia, nem o valor de cabeçalho
nenhum, nem a reivindicação que o chamador enviou. A resposta é composta só de
booleanos, contagens estritamente necessárias e classificações de um
vocabulário fixo declarado aqui. O gate `R05B-2` prova isso varrendo a saída
com entradas adversariais.

## O oráculo, dito em voz alta

`candidato_bate_com_origem_declarada` é, por definição, um oráculo de
igualdade: quem tem a chave pode testar endereços um a um. Isso é aceito
deliberadamente — a chave é do operador, a sonda é temporária e sai do
repositório quando a certificação fechar, e sem esse booleano a identidade
continua não observável. O que **não** é aceito é devolver o endereço, que
transformaria um oráculo lento em vazamento direto.

## Falha fechada

Sem `PROXY_CHAIN_PROBE_KEY` no ambiente, a rota devolve 404 — como se não
existisse. Sem modo aberto, sem variante pública, sem fallback por sessão.
"""

from __future__ import annotations

import hmac
import ipaddress
import os

# TEST-NET-1 (RFC 5737). Espaço de documentação, não roteável, que nenhuma
# infraestrutura real emite. Se um desses chega à aplicação, só pode ter vindo
# do cliente — é isso que o torna sentinela.
REDE_SENTINELA = ipaddress.ip_network('192.0.2.0/24')

#: Vocabulário fechado das classificações de cabeçalho (P3).
CLASSES_DE_CABECALHO = ('ausente', 'sentinela_sobrevive', 'substituida')

#: Presença reportada apenas para estes nomes. Lista fixa: nenhum cabeçalho
#: arbitrário — que poderia carregar dado no próprio nome — entra na resposta.
CABECALHOS_OBSERVADOS = (
    'X-Forwarded-For',
    'X-Forwarded-Proto',
    'CF-Connecting-Ip',
    'True-Client-Ip',
    'X-Real-Ip',
    'Forwarded',
    'Via',
)

#: Cabeçalhos de entrada que esta sonda consome.
CABECALHO_CHAVE = 'X-Diagnostics-Key'
CABECALHO_HOPS = 'X-Probe-Hops'
CABECALHO_REIVINDICACAO = 'X-Origin-Claim'
CABECALHO_REIVINDICACAO_ALT = 'X-Origin-Claim-Alt'

HOPS_MAXIMO = 16


def _cabecalho(handler, nome: str) -> str:
    """Lê um cabeçalho SEM depender da grafia nem do container.

    Em produção `handler.headers` é um `HTTPMessage`, que já é insensível a
    maiúsculas. Depender disso deixava a sonda frágil de dois jeitos: um gate
    com dicionário simples reprovava, e um cliente que mandasse
    `cf-connecting-ip` em outra grafia passaria despercebido. A busca abaixo
    resolve os dois — e o gate `R05B-8c` foi quem mostrou.
    """
    try:
        cabecalhos = handler.headers
    except Exception:  # noqa: BLE001 — leitura defensiva de handler arbitrário
        return ''
    try:
        direto = cabecalhos.get(nome)
        if direto:
            return str(direto).strip()
    except Exception:  # noqa: BLE001 — container arbitrário
        pass
    alvo = nome.lower()
    try:
        itens = cabecalhos.items()
    except Exception:  # noqa: BLE001 — container sem items()
        return ''
    for chave, valor in itens:
        if str(chave).lower() == alvo and valor:
            return str(valor).strip()
    return ''


def _e_sentinela(valor: str) -> bool:
    try:
        return ipaddress.ip_address(valor) in REDE_SENTINELA
    except ValueError:
        return False


def _normalizar(valor: str) -> str:
    """Forma canônica para comparar endereços sem depender de grafia.

    `203.0.113.9` e ` 203.0.113.009 ` não são a mesma string, e
    `::ffff:192.0.2.9` e `192.0.2.9` são o mesmo endereço. Comparar texto cru
    produziria `false` onde a resposta certa é `true`, e um P1 falso-negativo
    pareceria evidência de que a identidade não bate.
    """
    if not valor:
        return ''
    try:
        endereco = ipaddress.ip_address(valor)
    except ValueError:
        return ''
    if endereco.version == 6 and endereco.ipv4_mapped is not None:
        endereco = endereco.ipv4_mapped
    return str(endereco)


def _cadeia(handler) -> list:
    bruto = _cabecalho(handler, 'X-Forwarded-For')
    return [parte.strip() for parte in bruto.split(',') if parte.strip()]


def _hops_pedido(handler) -> int:
    """Quantos saltos avaliar. Vem do pedido porque o ambiente ainda declara 0:
    a sonda precisa conseguir avaliar o número PROPOSTO, não o configurado."""
    bruto = _cabecalho(handler, CABECALHO_HOPS)
    try:
        valor = int(bruto)
    except ValueError:
        return 0
    return max(0, min(valor, HOPS_MAXIMO))


def _classe_do_cabecalho(handler, nome: str) -> str:
    """P3. Diz se o valor recebido é o sentinela que o cliente mandou (logo o
    cliente controla o cabeçalho) ou outra coisa (logo a borda o reescreveu).
    Nunca devolve o valor.

    Olha TODOS os elementos, não só o primeiro. Uma borda que ANTEPÕE o próprio
    endereço e preserva o do cliente à direita — `real, 192.0.2.10` — faria a
    leitura do primeiro elemento dizer `substituida` com o sentinela vivo na
    mesma linha. O mesmo vale para instâncias repetidas do cabeçalho, que o
    container junta com vírgula. Achado de revisão: aqui um falso `substituida`
    é pior que um falso `sentinela_sobrevive`, porque leva a ADOTAR um
    cabeçalho que o cliente controla.
    """
    valor = _cabecalho(handler, nome)
    if not valor:
        return 'ausente'
    elementos = [parte.strip() for parte in valor.split(',') if parte.strip()]
    if any(_e_sentinela(elemento) for elemento in elementos):
        return 'sentinela_sobrevive'
    return 'substituida'


def analisar(cadeia: list, hops: int, reivindicacao: str, alternativa: str,
             classes: dict, presentes: list) -> dict:
    """Avalia P1–P4 sobre uma cadeia já extraída. Nunca devolve endereço.

    Separada do handler para que os gates possam exercitá-la com cadeias
    montadas à mão, sem inventar um objeto de requisição.
    """
    tamanho = len(cadeia)
    suficiente = hops >= 1 and tamanho >= hops

    indice_candidato = tamanho - hops if suficiente else None
    candidato = _normalizar(cadeia[indice_candidato]) if suficiente else ''

    # P4 — o sufixo que `cadeia[-hops]` usa sobreviveu inteiro?
    #
    # "Preservado" é definido como: nenhum dos `hops` elementos mais à direita
    # veio do cliente. É essa a região que a seleção consome, e é ela que um
    # truncamento pela direita destruiria — empurrando `cadeia[-hops]` para
    # dentro do que o cliente escreveu.
    #
    # Truncamento pela ESQUERDA não quebra a propriedade: ele descarta prefixo
    # do cliente, que já era ignorado. Por isso a definição olha só a janela.
    sufixo = cadeia[-hops:] if suficiente else []
    sufixo_preservado = bool(sufixo) and not any(_e_sentinela(e) for e in sufixo)

    # Guardas de contaminação (P1). A reivindicação NUNCA entra na construção
    # do candidato — ele sai da cadeia e só dela. Estes três booleanos deixam o
    # script provar que o teste não foi contaminado, em vez de assumir:
    #
    #   prefixo_do_cliente_presente  algum elemento é sentinela;
    #   cadeia_maior_que_hops        o cliente acrescentou algo à esquerda;
    #   reivindicacao_fora_do_candidato  o valor declarado aparece em OUTRA
    #                                    posição da cadeia — sinal de que o
    #                                    chamador o injetou.
    alvo = _normalizar(reivindicacao)
    fora_do_candidato = bool(alvo) and any(
        _normalizar(elemento) == alvo
        for i, elemento in enumerate(cadeia)
        if i != indice_candidato
    )

    bate = None
    if alvo and suficiente:
        bate = hmac.compare_digest(candidato.encode('utf-8'), alvo.encode('utf-8'))

    alvo_alt = _normalizar(alternativa)
    bate_alt = None
    if alvo_alt and suficiente:
        bate_alt = hmac.compare_digest(candidato.encode('utf-8'), alvo_alt.encode('utf-8'))

    return {
        'probe': 'R05B',
        'hops_avaliado': hops,
        'cadeia_tamanho': tamanho,
        'cadeia_suficiente_para_hops': suficiente,
        'sentinelas_na_cadeia': sum(1 for e in cadeia if _e_sentinela(e)),
        'prefixo_do_cliente_presente': any(_e_sentinela(e) for e in cadeia),
        'cadeia_maior_que_hops': tamanho > hops,
        'reivindicacao_fora_do_candidato': fora_do_candidato,
        'candidato_e_do_cliente': bool(suficiente) and _e_sentinela(cadeia[indice_candidato]),
        'sufixo_confiavel_preservado': sufixo_preservado,
        'candidato_bate_com_origem_declarada': bate,
        'candidato_bate_com_origem_alternativa': bate_alt,
        'cf_connecting_ip': classes.get('CF-Connecting-Ip', 'ausente'),
        'true_client_ip': classes.get('True-Client-Ip', 'ausente'),
        'cabecalhos_presentes': list(presentes),
    }


def chave_configurada() -> str:
    return str(os.environ.get('PROXY_CHAIN_PROBE_KEY', '')).strip()


def autorizado(handler) -> bool:
    chave = chave_configurada()
    if not chave:
        return False
    fornecida = _cabecalho(handler, CABECALHO_CHAVE)
    # Compara BYTES: com `str`, `compare_digest` levanta TypeError quando
    # qualquer lado tem caractere fora de ASCII, e a exceção viraria 500 —
    # distinguindo rota protegida de rota ausente, que é justamente o que o
    # 404 existe para impedir.
    return hmac.compare_digest(fornecida.encode('utf-8'), chave.encode('utf-8'))


def medir(handler) -> dict:
    """Ponto único de entrada do handler."""
    presentes = [nome for nome in CABECALHOS_OBSERVADOS if _cabecalho(handler, nome)]
    classes = {
        'CF-Connecting-Ip': _classe_do_cabecalho(handler, 'CF-Connecting-Ip'),
        'True-Client-Ip': _classe_do_cabecalho(handler, 'True-Client-Ip'),
    }
    return analisar(
        _cadeia(handler),
        _hops_pedido(handler),
        _cabecalho(handler, CABECALHO_REIVINDICACAO),
        _cabecalho(handler, CABECALHO_REIVINDICACAO_ALT),
        classes,
        presentes,
    )
