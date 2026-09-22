#!/usr/bin/env python3
"""R0.5 — determinação da cadeia de proxy em produção.

## O que este script responde

Um número: quantos proxies CONFIÁVEIS existem entre o cliente e a aplicação,
que é o valor correto de `RATE_LIMIT_TRUSTED_PROXY_HOPS`.

E, antes dele, a pergunta que precisa vir primeiro: a borda da plataforma
**anexa**, **sobrescreve** ou **higieniza** o `X-Forwarded-For` que o cliente
mandou? Enquanto isso não estiver respondido, nenhuma posição do cabeçalho é
confiável e o valor seguro continua sendo `0`.

## Estado: NOT DETERMINED até rodar

Enquanto este script não for executado com sucesso contra o deployment, a
cadeia fica **NOT DETERMINED**. Ausência de execução não é `1`, não é `0`, e
não é aprovação — é ausência de informação. Chamar isso de resposta é o mesmo
erro que o R0 já documentou: um gate verde pelo motivo errado.

Foi por isso que a R0 não chutou. A documentação da Render é inalcançável do
ambiente onde o código é escrito (o egresso nega `render.com`, `docs.render.com`
e `*.onrender.com` com 403 no CONNECT), e adivinhar `1` teria produzido um
sistema que parece configurado e está errado.

## Somente leitura

Só faz `GET`. Não escreve nada, não altera configuração, não autentica com
credencial de usuário. A única credencial que usa é a chave da própria sonda.

## Nada de dado real sai daqui

A sonda devolve apenas FORMA — contagens, posições, classificações e nomes de
cabeçalho. Nenhum endereço, nem o da borda, nem o de quem roda o script. O que
este relatório imprime é exatamente o que a sonda devolveu.

Os endereços que o script ENVIA são de `192.0.2.0/24` (TEST-NET-1, RFC 5737):
espaço de documentação, não roteável, que nenhuma infraestrutura real emite. É
isso que faz deles sentinelas: se um chega até a aplicação, só pode ter vindo
do cliente.

## Um número não sai de uma requisição só

Três controles, cada um repetido, e o valor só é aceito quando todos concordam:

- **A — sem `X-Forwarded-For`.** Mede quantos elementos a borda contribui por
  conta própria. É o controle que separa "a borda anexa" de "a borda não faz
  nada": sem ele, uma cadeia de tamanho 1 é ambígua.
- **B — um sentinela.** Mostra o que acontece com o que o cliente escreveu.
- **C — três sentinelas.** Repete a pergunta de B com uma cadeia mais longa. Se
  a borda anexa, a contribuição dela tem de ser a mesma de B; se depender do
  que o cliente mandou, o modelo está errado e o script recusa o número.

Divergência entre repetições da mesma sondagem também reprova: isso indicaria
mais de um caminho de borda, e um número médio não protege ninguém.

## Uma origem mede UM caminho, não a cadeia

`get_client_ip` lê `cadeia[-N]`. Se algum caminho de produção atravessar MENOS
proxies do que os N medidos aqui, nesse caminho `cadeia[-N]` é um elemento que
o CLIENTE escreveu — o bypass que a R0 fechou, reaberto com aparência de
medição.

Com `N=2` e um caminho de 1 proxy: o cliente manda `evil`, o proxy anexa o
endereço dele, a cadeia chega como `[evil, cliente]`, `len` não é menor que 2,
e `cadeia[-2]` devolve `evil`.

As três repetições de cada controle não ajudam aqui: elas saem todas da mesma
máquina e enxergam o mesmo caminho. Se o roteamento da borda depender de origem
ou região, este script pode observar, de forma perfeitamente consistente, uma
cadeia que não vale para os outros usuários.

Logo o valor seguro não é o que esta origem mediu: é o **menor** entre todos os
caminhos. Por isso o script mede, salva a forma, e só certifica quando uma
segunda origem independente produz a mesma forma:

    # primeira máquina (ex.: rede de casa)
    export EPI_PROXY_ORIGEM=casa
    export EPI_PROXY_SALVAR_MEDICAO=medicao-casa.json
    python3 scripts/certificar_cadeia_de_proxy.py        # -> [MEDIDO], saída 3

    # segunda máquina, rede DIFERENTE (ex.: 4G, VPS em outra região)
    export EPI_PROXY_ORIGEM=4g
    export EPI_PROXY_MEDICAO_ANTERIOR=medicao-casa.json
    python3 scripts/certificar_cadeia_de_proxy.py        # -> [DETERMINED], saída 0

O rótulo da origem é declarado pelo operador, e o script não tem como
verificá-lo. Está escrito assim de propósito: é um passo deliberado do
procedimento, não uma garantia do instrumento. O arquivo salvo guarda só FORMA
— as mesmas contagens e posições que a sonda devolve, nenhum endereço.

Achado levantado pela revisão automática do Codex (P1) e confirmado lendo
`core/rate_limit.py`: a versão anterior certificava, de uma origem só, um
número que reabriria o bypass nos caminhos mais curtos.

## Uso

    export EPI_PROXY_CORP_URL=https://...        # API corporativa
    export EPI_PROXY_CORP_KEY=...                # PROXY_CHAIN_PROBE_KEY do serviço
    export EPI_PROXY_SAAS_URL=https://...        # API do SaaS
    export EPI_PROXY_SAAS_KEY=...
    export EPI_PROXY_ORIGEM=casa                 # rótulo desta origem
    export EPI_PROXY_SALVAR_MEDICAO=...          # onde gravar a forma medida
    export EPI_PROXY_MEDICAO_ANTERIOR=...        # medição de OUTRA origem
    python3 scripts/certificar_cadeia_de_proxy.py

Definir `PROXY_CHAIN_PROBE_KEY` no serviço é o que liga a sonda. Sem ela, a
rota devolve 404 e este script reporta NOT DETERMINED — que é o comportamento
correto, não uma falha.

Saída: 0 = determinado E corroborado por duas origens · 1 = medições
inconsistentes ou ambientes divergentes · 2 = não executado/não determinado ·
3 = medido numa origem só, falta corroborar.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROTA = '/api/proxy-chain-diagnostics'
TIMEOUT = 30
REPETICOES = 3

# TEST-NET-1 (RFC 5737). Documentação, não roteável, nunca emitido por
# infraestrutura real — por isso serve de sentinela.
SENTINELA_UNICO = '192.0.2.10'
SENTINELA_CADEIA = '192.0.2.10, 192.0.2.11, 192.0.2.12'

# Os campos que decidem o número. Se algum destes variar entre repetições da
# mesma sondagem, não há cadeia única para determinar.
CAMPOS_DECISIVOS = (
    'cadeia_tamanho',
    'sentinela_presente',
    'sentinela_indice',
    'elementos_a_direita_do_sentinela',
    'veredito',
)


class NaoDeterminado(Exception):
    """Falta informação. Diferente de medição inconsistente."""


class Inconsistente(Exception):
    """Mediu, e as medições se contradizem."""


class _RecusaRedirecionamento(urllib.request.HTTPRedirectHandler):
    """A chave da sonda viaja em cabeçalho, e o `urllib` COPIA os cabeçalhos
    para o destino do redirecionamento — só `content-length` e `content-type`
    ficam de fora. Um redirect de canonicalização (apex → www, http → https)
    ou uma configuração errada entregaria o segredo a outro host.

    Diagnóstico não segue redirecionamento. Quem informou a URL informa a
    final."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NaoDeterminado(
            f'a URL respondeu com redirecionamento (HTTP {code}). Informe a URL '
            'final: a sonda não segue redirect para não expor a chave a outro host'
        )


_ABRIDOR = urllib.request.build_opener(_RecusaRedirecionamento)


def _sondar(base_url: str, chave: str, xff: str | None) -> dict:
    url = base_url.rstrip('/') + ROTA
    # A recusa de redirecionamento protege o SEGUNDO salto; esta checagem
    # protege o primeiro. Com `http://`, a chave iria em claro na rede antes de
    # existir redirect algum — um `s` esquecido ao copiar a URL bastava.
    if not url.lower().startswith('https://'):
        raise NaoDeterminado(
            'a URL precisa ser https. A chave da sonda viaja em cabeçalho e '
            'seria enviada em claro'
        )
    req = urllib.request.Request(url, method='GET')
    req.add_header('X-Diagnostics-Key', chave)
    if xff is not None:
        req.add_header('X-Forwarded-For', xff)
    try:
        with _ABRIDOR.open(req, timeout=TIMEOUT) as resp:
            corpo = resp.read().decode('utf-8', errors='replace')
            if resp.status != 200:
                raise NaoDeterminado(f'HTTP {resp.status} em {ROTA}')
            dados = json.loads(corpo)
            # `json.loads` aceita qualquer JSON válido, inclusive `[]` e
            # `"ok"`. Uma URL errada, um proxy corporativo que responde por
            # conta própria ou uma sonda de outra versão devolvem isso — e o
            # valor escapava daqui para `_forma`, que chama `.get` e estourava
            # AttributeError. O script morria com traceback justamente no caso
            # que ele existe para diagnosticar.
            if not isinstance(dados, dict):
                raise NaoDeterminado(
                    f'a resposta é JSON mas não é um objeto '
                    f'({type(dados).__name__}) — a URL aponta mesmo para a sonda?'
                )
            return dados
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NaoDeterminado(
                'sonda desligada (404) — defina PROXY_CHAIN_PROBE_KEY no serviço '
                'e use a mesma chave aqui'
            ) from e
        raise NaoDeterminado(f'HTTP {e.code} em {ROTA}') from e
    except json.JSONDecodeError as e:
        raise NaoDeterminado('resposta não é JSON — a rota existe mesmo?') from e
    except NaoDeterminado:
        raise  # já tem mensagem própria (ex.: recusa de redirecionamento)
    except Exception as e:  # noqa: BLE001 — rede é imprevisível; vira relatório
        raise NaoDeterminado(f'não alcançou o serviço: {e}') from e


def _forma(amostra: dict) -> tuple:
    return tuple(amostra.get(campo) for campo in CAMPOS_DECISIVOS)


def _controle(nome: str, base_url: str, chave: str, xff: str | None) -> dict:
    """Roda a mesma sondagem `REPETICOES` vezes e exige que concordem."""
    amostras = [_sondar(base_url, chave, xff) for _ in range(REPETICOES)]
    formas = {_forma(a) for a in amostras}
    if len(formas) != 1:
        raise Inconsistente(
            f'controle {nome}: {len(formas)} formas diferentes em {REPETICOES} '
            f'sondagens — há mais de um caminho de borda'
        )
    return amostras[0]


def _contribuicao_da_borda(amostra: dict) -> int:
    """Quantos elementos a BORDA pôs na cadeia, e não o cliente.

    Com sentinela presente, é o que ficou à direita dele. Sem sentinela, o
    cliente não sobreviveu: a cadeia inteira é da borda.
    """
    if amostra.get('sentinela_presente'):
        return int(amostra.get('elementos_a_direita_do_sentinela') or 0)
    return int(amostra.get('cadeia_tamanho') or 0)


class Determinacao:
    def __init__(self, ambiente: str) -> None:
        self.ambiente = ambiente
        self.executado = False
        self.motivo = ''
        self.valor: int | None = None
        self.veredito = ''
        self.colapso = False
        #: True quando as medições se CONTRADIZEM. Diferente de medir de forma
        #: consistente e a forma medida não bastar para concluir — os dois
        #: impedem configurar, mas pedem ações diferentes do operador.
        self.contradicao = False
        self.evidencia: list[tuple[str, dict]] = []

    @property
    def determinado(self) -> bool:
        return self.executado and self.valor is not None


def determinar(ambiente: str, base_url: str, chave: str) -> Determinacao:
    resultado = Determinacao(ambiente)
    if not base_url or not chave:
        resultado.motivo = 'variáveis de ambiente ausentes — não executado'
        return resultado

    try:
        sem_xff = _controle('A (sem XFF)', base_url, chave, None)
        um = _controle('B (um sentinela)', base_url, chave, SENTINELA_UNICO)
        tres = _controle('C (três sentinelas)', base_url, chave, SENTINELA_CADEIA)
    except NaoDeterminado as e:
        resultado.motivo = str(e)
        return resultado
    except Inconsistente as e:
        resultado.executado = True
        resultado.contradicao = True
        resultado.motivo = str(e)
        return resultado

    resultado.executado = True
    resultado.evidencia = [
        ('A · sem X-Forwarded-For', sem_xff),
        ('B · um sentinela', um),
        ('C · três sentinelas', tres),
    ]

    # Os DOIS sinais juntos, não um ou outro. Numa implantação direta, sem
    # borda nenhuma, a cadeia vem vazia e o peer não está nela — mas esse peer
    # É o cliente. Com `or`, esse caso disparava o aviso de colapso e o
    # relatório afirmava que a auditoria grava o endereço da borda onde borda
    # não existe. O texto ao lado já descrevia a conjunção; o código é que
    # estava escrito com disjunção.
    #
    # Continua sendo heurística: uma borda com endereço público se parece com
    # um cliente direto. Prova mesmo só com duas origens distintas.
    resultado.colapso = (
        sem_xff.get('peer_classe') == 'privado' and not sem_xff.get('peer_na_cadeia')
    )

    n_borda = _contribuicao_da_borda(sem_xff)
    contrib_b = _contribuicao_da_borda(um)
    contrib_c = _contribuicao_da_borda(tres)

    if um.get('veredito') != tres.get('veredito'):
        resultado.contradicao = True
        resultado.motivo = (
            f"B e C discordam do modelo: {um.get('veredito')} × {tres.get('veredito')} "
            '— o tratamento da borda depende do que o cliente manda'
        )
        return resultado

    resultado.veredito = str(um.get('veredito') or 'INDETERMINADO')

    if resultado.veredito == 'INDETERMINADO':
        resultado.motivo = (
            'algo foi inserido à ESQUERDA do que o cliente mandou — não é '
            'nenhum dos modelos conhecidos; recusar é mais honesto que ler errado'
        )
        return resultado

    if not (n_borda == contrib_b == contrib_c):
        resultado.contradicao = True
        resultado.motivo = (
            f'contribuição da borda não é constante: A={n_borda} · B={contrib_b} '
            f'· C={contrib_c} — o número dependeria do que o cliente enviou'
        )
        return resultado

    if resultado.veredito == 'PASSA_DIRETO':
        # O sentinela chegou sozinho: a borda não acrescenta nada, logo o
        # cabeçalho inteiro é escolha do cliente. `0` não é um default aqui —
        # é a resposta.
        resultado.valor = 0
        return resultado

    if resultado.veredito == 'SOBRESCREVE':
        # Forma constante NÃO prova que o elemento restante seja o cliente.
        # Contraexemplo: dois proxies, e o interno sobrescreve o cabeçalho com
        # o peer DELE — que é o proxy externo. Os três controles produzem, de
        # forma perfeitamente consistente, uma cadeia de um elemento sem
        # sentinela. Certificar 1 aqui faria `get_client_ip` devolver o proxy
        # externo para todo mundo e colapsar os buckets: exatamente o dano que
        # esta frente existe para evitar, agora com aparência de medição.
        #
        # Separar os casos exigiria observar de DUAS origens distintas que o
        # elemento escolhido muda com o cliente. O script tem um ponto de vista
        # só, então recusa — recusar é mais honesto que ler errado.
        resultado.motivo = (
            'a borda SOBRESCREVE o cabeçalho, e a forma constante não prova que '
            'o elemento restante represente o cliente. Um proxy interno que '
            'escreve o próprio peer produz esta mesma medição e faria todos os '
            'usuários caírem num bucket só. Determinar exige observar, de duas '
            'origens distintas, que o elemento escolhido varia com o cliente.'
        )
        return resultado

    # Lista de PERMISSÃO explícita, não queda por exaustão. Uma sonda com
    # versão diferente, ou com resposta malformada, pode devolver um veredito
    # que este script não conhece; se B e C concordarem nele e as contribuições
    # baterem, a versão anterior chegava aqui e recomendava um número para um
    # modelo que ela não entende. Falhar fechado é a única leitura honesta.
    if resultado.veredito not in ('ANEXA', 'HIGIENIZA'):
        resultado.motivo = (
            f'veredito {resultado.veredito!r} não é um modelo que este script '
            'saiba converter em número. Versão da sonda diferente da esperada?'
        )
        return resultado

    resultado.valor = n_borda
    return resultado


# ── Corroboração por uma segunda origem ─────────────────────────────────────
#
# O raciocínio está no topo do arquivo. Aqui só a mecânica: guardar a FORMA
# medida, e comparar com a forma que outra origem mediu. Nenhum endereço entra
# no arquivo — os campos salvos são os mesmos que a sonda devolve.

VERSAO_DA_MEDICAO = 1


def _forma_da_determinacao(r: Determinacao) -> dict:
    return {
        'ambiente': r.ambiente,
        'veredito': r.veredito,
        'valor': r.valor,
        'controles': [
            {campo: amostra.get(campo) for campo in CAMPOS_DECISIVOS}
            for _, amostra in r.evidencia
        ],
    }


def _salvar_medicao(caminho: str, origem: str, resultados: list) -> str:
    dados = {
        'versao': VERSAO_DA_MEDICAO,
        'origem': origem,
        'ambientes': [_forma_da_determinacao(r) for r in resultados if r.determinado],
    }
    with open(caminho, 'w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2, sort_keys=True)
    return caminho


def _carregar_medicao(caminho: str) -> dict:
    try:
        with open(caminho, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
    except OSError as e:
        raise NaoDeterminado(f'não consegui ler a medição anterior: {e}') from e
    except json.JSONDecodeError as e:
        raise NaoDeterminado(f'a medição anterior não é JSON válido: {e}') from e
    if not isinstance(dados, dict) or dados.get('versao') != VERSAO_DA_MEDICAO:
        raise NaoDeterminado(
            'a medição anterior não tem o formato esperado — gere-a de novo '
            'com esta versão do script'
        )
    if not str(dados.get('origem') or '').strip():
        raise NaoDeterminado('a medição anterior não declara a origem')
    return dados


def _corroborar(resultados: list, origem: str, anterior: dict) -> tuple:
    """Confere se outra origem mediu a MESMA forma. Devolve (certifica, motivo)."""
    origem_anterior = str(anterior.get('origem') or '').strip()
    if origem and origem == origem_anterior:
        return False, (
            f'a medição anterior declara a MESMA origem ({origem!r}). Duas '
            'medições do mesmo caminho não dizem nada sobre os outros caminhos'
        )
    por_ambiente = {a.get('ambiente'): a for a in (anterior.get('ambientes') or [])}
    determinados = [r for r in resultados if r.determinado]
    if not determinados:
        return False, 'nada determinado nesta origem para corroborar'
    for r in determinados:
        antes = por_ambiente.get(r.ambiente)
        if antes is None:
            return False, (
                f'a medição de {origem_anterior!r} não cobre o ambiente '
                f'{r.ambiente!r}'
            )
        agora = _forma_da_determinacao(r)
        if (antes.get('veredito'), antes.get('valor')) != (agora['veredito'], agora['valor']):
            return False, (
                f'{r.ambiente}: as origens discordam — {origem_anterior!r} mediu '
                f'{antes.get("veredito")}/{antes.get("valor")} e {origem!r} mediu '
                f'{agora["veredito"]}/{agora["valor"]}. O roteamento da borda '
                'depende da origem, e o valor seguro é o MENOR de todos os '
                'caminhos: provar um mínimo exige medir todas as rotas, não duas'
            )
        if antes.get('controles') != agora['controles']:
            return False, (
                f'{r.ambiente}: o veredito e o número batem, mas a forma dos '
                'controles difere entre as origens — há mais de um caminho de '
                'borda e a leitura não é única'
            )
    return True, f'{origem_anterior!r} e {origem!r} mediram a mesma forma'


def _linha_evidencia(rotulo: str, amostra: dict) -> str:
    return (
        f'    {rotulo:26} cadeia={amostra.get("cadeia_tamanho")} '
        f'sentinela={"sim" if amostra.get("sentinela_presente") else "não"}'
        f'@{amostra.get("sentinela_indice")} '
        f'à_direita={amostra.get("elementos_a_direita_do_sentinela")} '
        f'peer_na_cadeia={"sim" if amostra.get("peer_na_cadeia") else "não"}'
        f'@{amostra.get("peer_indice")} '
        f'peer={amostra.get("peer_classe")} '
        f'veredito={amostra.get("veredito")}'
    )


def main() -> int:
    origem = os.environ.get('EPI_PROXY_ORIGEM', '').strip()
    caminho_anterior = os.environ.get('EPI_PROXY_MEDICAO_ANTERIOR', '').strip()
    caminho_salvar = os.environ.get('EPI_PROXY_SALVAR_MEDICAO', '').strip()

    # Carregada ANTES de sondar: descobrir que o arquivo não serve depois de
    # nove requisições seria desperdiçar a ida ao serviço.
    anterior = None
    erro_anterior = ''
    if caminho_anterior:
        try:
            anterior = _carregar_medicao(caminho_anterior)
        except NaoDeterminado as e:
            erro_anterior = str(e)

    alvos = [
        ('corporativo', os.environ.get('EPI_PROXY_CORP_URL', ''),
         os.environ.get('EPI_PROXY_CORP_KEY', '')),
        ('saas', os.environ.get('EPI_PROXY_SAAS_URL', ''),
         os.environ.get('EPI_PROXY_SAAS_KEY', '')),
    ]
    resultados = [determinar(nome, url, chave) for nome, url, chave in alvos]

    print('=' * 72)
    print('DETERMINAÇÃO DA CADEIA DE PROXY — R0.5')
    print('=' * 72)

    nao_executado = False
    inconsistente = False

    for r in resultados:
        print()
        if not r.executado:
            nao_executado = True
            print(f'[NOT DETERMINED] {r.ambiente}')
            print(f'   {r.motivo}')
            continue

        # A evidência vem VAZIA quando as repetições se contradizem: o
        # `determinar` desiste antes de montar os controles. Indexar aqui
        # estourava IndexError justamente no caso que o script existe para
        # diagnosticar — o relatório morria antes de dizer o que houve.
        if r.evidencia:
            for rotulo, amostra in r.evidencia:
                print(_linha_evidencia(rotulo, amostra))
            cabecalhos = r.evidencia[0][1].get('cabecalhos_de_forwarding') or []
            print(f'    {"cabeçalhos recebidos":26} {", ".join(cabecalhos) or "(nenhum)"}')
            print()

        if r.valor is None:
            if r.contradicao:
                inconsistente = True
                print(f'[INCONSISTENT] {r.ambiente}')
            else:
                nao_executado = True
                print(f'[NOT DETERMINED] {r.ambiente}')
            print(f'   {r.motivo}')
            continue

        # `MEDIDO`, não `DETERMINED`: esta origem mediu um caminho. O
        # veredito final só sai no rodapé, depois da corroboração.
        print(f'[MEDIDO] {r.ambiente} — borda {r.veredito}')
        print(f'   RATE_LIMIT_TRUSTED_PROXY_HOPS={r.valor} (medido desta origem)')
        if r.valor == 0:
            print('   A borda não contribui com nada confiável para o cabeçalho.')
            print('   O peer do socket continua sendo a única origem honesta.')
        if r.colapso:
            print('   ATENÇÃO: o peer que a aplicação enxerga é da borda, não do')
            print('   cliente. Todo ponto que grava `client_address[0]` como IP')
            print('   de auditoria está gravando o endereço da borda.')

    print()
    print('=' * 72)
    if inconsistente:
        print('RESULTADO: medições inconsistentes — NÃO configure nenhum valor.')
        return 1
    if nao_executado:
        print('RESULTADO: NOT DETERMINED — mantenha RATE_LIMIT_TRUSTED_PROXY_HOPS=0.')
        return 2
    # Valor E modelo. `HIGIENIZA` e `PASSA_DIRETO` produzem os dois o valor
    # `0`, então comparar só o número dizia "determinada" enquanto os dois
    # ambientes tinham bordas de modelos diferentes. O contrato registra
    # `MODELO-DA-BORDA` e é idêntico nos dois repositórios: fechar os dois a
    # partir desse sucesso gravaria um modelo errado em um deles.
    assinaturas = {(r.valor, r.veredito) for r in resultados if r.determinado}
    if len(assinaturas) > 1:
        print('RESULTADO: os dois ambientes têm cadeias DIFERENTES.')
        for r in resultados:
            if r.determinado:
                print(f'   {r.ambiente}: borda {r.veredito} → {r.valor}')
        print('Cada repositório precisa do seu próprio contrato — não unifique.')
        return 1

    if caminho_salvar:
        try:
            _salvar_medicao(caminho_salvar, origem or '(sem rótulo)', resultados)
            print(f'Forma desta origem gravada em {caminho_salvar}.')
        except OSError as e:
            print(f'AVISO: não consegui gravar a medição — {e}')

    if erro_anterior:
        print(f'RESULTADO: MEDIDO, mas a medição anterior não serviu — {erro_anterior}')
        return 3
    if anterior is None:
        print('RESULTADO: MEDIDO numa origem só — ainda NÃO configure nada.')
        print('Uma origem mede um caminho, não a cadeia. Repita de uma rede')
        print('independente com EPI_PROXY_MEDICAO_ANTERIOR apontando para a')
        print('forma salva aqui.')
        return 3
    if not origem:
        print('RESULTADO: MEDIDO, mas esta origem não declarou EPI_PROXY_ORIGEM.')
        print('Sem rótulo não há como afirmar que as duas medições vieram de')
        print('caminhos diferentes.')
        return 3

    corrobora, motivo = _corroborar(resultados, origem, anterior)
    if not corrobora:
        print(f'RESULTADO: NÃO corroborado — {motivo}')
        return 1
    print(f'RESULTADO: cadeia determinada e corroborada por duas origens ({motivo}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
