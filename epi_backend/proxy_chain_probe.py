"""R0.5 — sonda TEMPORÁRIA da cadeia de proxy.

## Por que ela existe

A R0 fechou o buraco de o cliente escolher o próprio bucket de rate limiting,
e deixou a confiança DECLARADA em `RATE_LIMIT_TRUSTED_PROXY_HOPS`, com padrão
`0` — ignore o cabeçalho, use o peer do socket.

`0` é seguro contra spoofing e pode estar operacionalmente errado: se todos os
acessos chegam pelo mesmo peer da borda, o limitador enxerga milhares de
pessoas como uma origem só. Descobrir qual é o número certo exige saber o que a
aplicação REALMENTE recebe — e isso não se lê em código, só se mede em runtime.

Esta sonda mede. Ela não decide nada e não é consumida por nenhum caminho de
produção: `core/rate_limit.py` continua lendo apenas a variável de ambiente.

## Por que ela é temporária

Diagnóstico não vira API. Assim que a cadeia for determinada e registrada em
`docs/R05_CADEIA_DE_PROXY.md`, este arquivo e o seu registro de rota saem do
repositório. O gate `R05-9` existe exatamente para isso: quando o contrato
deixar de ser `INDETERMINADO`, a presença deste módulo reprova a suíte.

## O que ela nunca devolve

Nenhum endereço. Nem o peer, nem elementos do `X-Forwarded-For`, nem valor de
cabeçalho nenhum. A saída é só FORMA: contagens, posições, classificações e
nomes de cabeçalho vindos de uma lista fixa. O gate `R05-3` prova isso por
varredura adversarial da saída.

## Falha fechada

Sem `PROXY_CHAIN_PROBE_KEY` definida no ambiente, a sonda não responde — o
handler devolve 404, como se a rota não existisse. Não há modo aberto, não há
variante pública e não há fallback por sessão autenticada: uma sonda que
descreve topologia de rede não tem versão "pública" que seja útil.
"""

from __future__ import annotations

import hmac
import ipaddress
import os

# TEST-NET-1 (RFC 5737). Endereços de documentação: não são roteáveis e nenhuma
# infraestrutura real os emite. Se um deles chega até a aplicação, ele só pode
# ter vindo do cliente — é isso que faz dele um sentinela confiável.
REDE_SENTINELA = ipaddress.ip_network('192.0.2.0/24')

# Presença é reportada apenas para estes nomes. Lista fixa: assim nenhum
# cabeçalho arbitrário — que poderia carregar dado de usuário no próprio nome —
# entra na resposta.
CABECALHOS_DE_FORWARDING = (
    'X-Forwarded-For',
    'X-Forwarded-Proto',
    'X-Forwarded-Host',
    'X-Forwarded-Port',
    'X-Real-Ip',
    'Forwarded',
    'Via',
    'CF-Connecting-Ip',
    'True-Client-Ip',
    'X-Client-Ip',
)

VEREDITOS = ('ANEXA', 'SOBRESCREVE', 'HIGIENIZA', 'PASSA_DIRETO', 'INDETERMINADO')


def _e_sentinela(elemento: str) -> bool:
    try:
        return ipaddress.ip_address(elemento) in REDE_SENTINELA
    except ValueError:
        return False


def _classe_do_endereco(valor: str) -> str:
    """Classifica sem revelar. 'privado' cobre RFC1918, loopback e CGNAT."""
    if not valor:
        return 'indisponivel'
    try:
        endereco = ipaddress.ip_address(valor)
    except ValueError:
        return 'nao_e_ip'
    if endereco.is_loopback or endereco.is_private:
        return 'privado'
    return 'publico'


def analisar(cadeia_bruta: str, peer: str, cabecalhos_presentes) -> dict:
    """Descreve a FORMA da cadeia recebida. Nunca devolve endereço.

    `cadeia_bruta` é o valor cru do `X-Forwarded-For`; `peer` é o endereço da
    outra ponta do socket; `cabecalhos_presentes` são os nomes já filtrados
    pela lista fixa acima.
    """
    cadeia = [parte.strip() for parte in (cadeia_bruta or '').split(',') if parte.strip()]

    indices_sentinela = [i for i, elemento in enumerate(cadeia) if _e_sentinela(elemento)]
    sentinela_presente = bool(indices_sentinela)
    # O último sentinela é a referência: um controle manda uma cadeia inteira de
    # sentinelas, e o que interessa é quantos elementos a borda acrescentou
    # DEPOIS do que o cliente escreveu.
    indice_sentinela = indices_sentinela[-1] if sentinela_presente else None
    a_direita = (len(cadeia) - 1 - indice_sentinela) if sentinela_presente else None

    peer_indice = None
    if peer:
        for i, elemento in enumerate(cadeia):
            if elemento == peer:
                peer_indice = i
                break

    if not cadeia:
        veredito = 'HIGIENIZA'
    elif not sentinela_presente:
        veredito = 'SOBRESCREVE'
    elif indices_sentinela[0] != 0:
        # Alguém pôs algo à ESQUERDA do que o cliente mandou. Não é nenhum dos
        # modelos conhecidos; recusar é mais honesto que inventar uma leitura.
        veredito = 'INDETERMINADO'
    elif a_direita == 0:
        veredito = 'PASSA_DIRETO'
    else:
        veredito = 'ANEXA'

    return {
        'cadeia_tamanho': len(cadeia),
        'sentinela_presente': sentinela_presente,
        'sentinela_indice': indice_sentinela,
        'elementos_a_direita_do_sentinela': a_direita,
        'peer_na_cadeia': peer_indice is not None,
        'peer_indice': peer_indice,
        'peer_classe': _classe_do_endereco(peer),
        'cabecalhos_de_forwarding': list(cabecalhos_presentes),
        'veredito': veredito,
    }


def _cabecalhos_presentes(handler) -> list:
    presentes = []
    for nome in CABECALHOS_DE_FORWARDING:
        try:
            valor = handler.headers.get(nome, '')
        except Exception:  # noqa: BLE001 — leitura defensiva de handler arbitrário
            valor = ''
        if valor:
            presentes.append(nome)
    return presentes


def _peer(handler) -> str:
    try:
        return str(handler.client_address[0])
    except Exception:  # noqa: BLE001 — mesmo padrão de core/rate_limit.py
        return ''


def chave_configurada() -> str:
    return str(os.environ.get('PROXY_CHAIN_PROBE_KEY', '')).strip()


def autorizado(handler) -> bool:
    chave = chave_configurada()
    if not chave:
        return False
    try:
        fornecida = str(handler.headers.get('X-Diagnostics-Key', '')).strip()
    except Exception:  # noqa: BLE001 — sem cabeçalho legível, não autoriza
        return False
    # Compara BYTES, não `str`. Com `str`, `compare_digest` levanta TypeError
    # quando qualquer lado tem caractere fora de ASCII — e a exceção escaparia
    # daqui, virando 500. Isso quebraria justamente a propriedade que o 404
    # existe para dar: quem sonda não distingue rota ausente de rota protegida.
    # Um 500 distinguiria.
    return hmac.compare_digest(fornecida.encode('utf-8'), chave.encode('utf-8'))


def medir(handler) -> dict:
    """Ponto único de entrada do handler. Só forma, nunca valores."""
    try:
        cadeia_bruta = handler.headers.get('X-Forwarded-For', '') or ''
    except Exception:  # noqa: BLE001 — ausência de cabeçalho é dado, não erro
        cadeia_bruta = ''
    return analisar(cadeia_bruta, _peer(handler), _cabecalhos_presentes(handler))
