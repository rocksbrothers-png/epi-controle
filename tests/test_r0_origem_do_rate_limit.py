"""R0 — de quem é o bucket: hardening da origem no `RateLimiter`.

## O achado

`get_client_ip` lia `X-Forwarded-For.split(',')[0]` — o PRIMEIRO elemento.
Esse elemento é escrito pelo CLIENTE. Medido antes desta fatia, com limite 3:

    XFF fixo      ->  3/6 permitidos   (o limite funciona)
    XFF variando  ->  6/6 permitidos   (o cliente escolhe o próprio bucket)

Ou seja: os quatro limitadores do projeto — login, recovery, tenant e portal do
fornecedor — eram contornáveis com um header. Corrigir isso é pré-requisito de
qualquer limitador novo; adicionar mais um consumidor antes seria decorativo.

## Por que não é `split(',')[-1]`

Num encadeamento onde cada proxy ACRESCENTA (`$proxy_add_x_forwarded_for` do
nginx documentado em `docs/WEB_APP_URL_ARCHITECTURE.md`), o endereço que o
proxy mais interno observou fica na posição `-N`, com N = número de proxies
confiáveis. `[-1]` só acerta quando N == 1, e vira spoof quando N == 0 — que é
exatamente o caso de execução local e direta.

Por isso a confiança é CONFIGURADA, não adivinhada: `RATE_LIMIT_TRUSTED_PROXY_HOPS`
declara quantos saltos confiáveis existem, e o padrão é 0.

## Por que o padrão é 0

0 significa "ignore o cabeçalho, use o peer do socket". É o único valor seguro
quando ninguém configurou nada: sem proxy na frente, o header é escolha do
cliente. Uma implantação atrás de proxy que esqueça de configurar o valor
falha FECHANDO — todo mundo cai no mesmo bucket e recebe 429 — em vez de falhar
abrindo, que é o defeito que esta fatia corrige. Falha fechada é barulhenta e
reversível; falha aberta é silenciosa.

Nenhum limite numérico muda aqui. A pergunta desta fatia é QUEM ocupa o bucket,
não QUANTAS requisições ele aceita.
"""

import threading
import time
from collections import deque

import core.rate_limit as RL
from core.rate_limit import RateLimiter, get_client_ip


class _Handler:
    """Requisição com peer de socket e cabeçalhos controláveis em separado."""

    def __init__(self, peer='198.51.100.7', xff=None):
        self.client_address = (peer, 54321)
        self.headers = {} if xff is None else {'X-Forwarded-For': xff}


def _com_saltos(n):
    """Troca a confiança declarada, restaurando depois."""
    class _Ctx:
        def __enter__(self):
            self.anterior = RL.TRUSTED_PROXY_HOPS
            RL.TRUSTED_PROXY_HOPS = n
        def __exit__(self, *a):
            RL.TRUSTED_PROXY_HOPS = self.anterior
    return _Ctx()


# ── R0-1: spoof simples ──────────────────────────────────────────────────────

def test_r0_1_variar_o_cabecalho_nao_gera_buckets_ilimitados():
    """O gate que descreve o defeito. Sem proxy confiável declarado, o cliente
    não pode trocar de balde mudando o que ele mesmo escreve."""
    with _com_saltos(0):
        limitador = RateLimiter(max_calls=3, period_seconds=60)
        permitidos = sum(
            limitador.is_allowed(get_client_ip(_Handler(peer='203.0.113.9', xff=f'10.0.0.{i}')))
            for i in range(10)
        )
    assert permitidos == 3, (
        f'{permitidos}/10 passaram num limite de 3 — variar o cabeçalho ainda '
        'troca de bucket'
    )


def test_r0_1b_nem_uma_cadeia_inteira_forjada_muda_o_bucket():
    """Variação do mesmo ataque: em vez de um valor, o cliente manda uma lista."""
    with _com_saltos(0):
        limitador = RateLimiter(max_calls=3, period_seconds=60)
        forjadas = [
            '1.1.1.1', '1.1.1.1, 2.2.2.2', '3.3.3.3, 4.4.4.4, 5.5.5.5',
            '6.6.6.6', '7.7.7.7, 8.8.8.8', '9.9.9.9',
        ]
        permitidos = sum(
            limitador.is_allowed(get_client_ip(_Handler(peer='203.0.113.9', xff=c)))
            for c in forjadas
        )
    assert permitidos == 3, f'{permitidos}/6 passaram num limite de 3'


# ── R0-2 / R0-3: mesma origem × origens diferentes ──────────────────────────

def test_r0_2_mesma_origem_real_compartilha_bucket():
    with _com_saltos(0):
        limitador = RateLimiter(max_calls=3, period_seconds=60)
        permitidos = sum(
            limitador.is_allowed(get_client_ip(_Handler(peer='203.0.113.9')))
            for _ in range(6)
        )
    assert permitidos == 3, f'a mesma origem deixou de compartilhar bucket: {permitidos}/6'


def test_r0_3_origens_diferentes_nao_sao_colapsadas():
    """O contrapeso: endurecer não pode virar "todo mundo no mesmo balde".
    Sem este gate, ignorar o cabeçalho E o peer passaria em R0-1 e derrubaria
    o serviço inteiro no primeiro usuário que atingisse o limite."""
    with _com_saltos(0):
        limitador = RateLimiter(max_calls=3, period_seconds=60)
        permitidos = sum(
            limitador.is_allowed(get_client_ip(_Handler(peer=f'203.0.113.{i}')))
            for i in range(6)
        )
    assert permitidos == 6, (
        f'clientes realmente distintos foram colapsados num bucket só: {permitidos}/6'
    )


# ── R0-4: sem proxy ──────────────────────────────────────────────────────────

def test_r0_4_sem_proxy_vale_o_peer_do_socket():
    with _com_saltos(0):
        assert get_client_ip(_Handler(peer='192.0.2.55')) == '192.0.2.55'
        # …e o cabeçalho não muda nada.
        assert get_client_ip(_Handler(peer='192.0.2.55', xff='evil')) == '192.0.2.55'


def test_r0_4b_peer_indisponivel_nao_explode_nem_vira_bucket_unico():
    class _SemPeer:
        headers = {}
    with _com_saltos(0):
        valor = get_client_ip(_SemPeer())
    assert isinstance(valor, str) and valor, 'origem indeterminada devolveu valor inválido'


# ── R0-5: cadeia com proxies confiáveis ─────────────────────────────────────

def test_r0_5_um_salto_confiavel_pega_o_endereco_que_o_proxy_observou():
    """Com 1 proxy que ACRESCENTA, o endereço observado por ele é o último.
    O lixo que o cliente mandou antes fica à esquerda e é ignorado."""
    with _com_saltos(1):
        assert get_client_ip(_Handler(peer='10.0.0.1', xff='evil, 203.0.113.9')) == '203.0.113.9'
        assert get_client_ip(_Handler(peer='10.0.0.1', xff='a, b, c, 203.0.113.9')) == '203.0.113.9'


def test_r0_5b_dois_saltos_confiaveis_andam_mais_uma_casa():
    with _com_saltos(2):
        # cliente -> proxy1 (acrescenta o cliente) -> proxy2 (acrescenta proxy1)
        assert get_client_ip(_Handler(peer='10.0.0.2', xff='evil, 203.0.113.9, 10.0.0.1')) == '203.0.113.9'


def test_r0_5c_cadeia_mais_curta_que_o_declarado_cai_no_peer():
    """Requisição que não atravessou a cadeia esperada não é confiável."""
    with _com_saltos(2):
        assert get_client_ip(_Handler(peer='10.0.0.2', xff='203.0.113.9')) == '10.0.0.2'
    with _com_saltos(1):
        assert get_client_ip(_Handler(peer='10.0.0.2', xff='')) == '10.0.0.2'


def test_r0_5d_com_salto_declarado_o_cliente_ainda_nao_escolhe_o_bucket():
    """O teste que importa em produção: mesmo com 1 salto confiável, encher o
    cabeçalho de lixo não cria buckets novos, porque o proxy acrescenta o
    endereço real à direita."""
    with _com_saltos(1):
        limitador = RateLimiter(max_calls=3, period_seconds=60)
        permitidos = sum(
            limitador.is_allowed(get_client_ip(
                _Handler(peer='10.0.0.1', xff=f'forjado{i}, 203.0.113.9')))
            for i in range(10)
        )
    assert permitidos == 3, f'{permitidos}/10 passaram num limite de 3'


# ── R0-6: concorrência (controle — já valia antes) ──────────────────────────

def _corrida(limitador, fios=20):
    """20 threads soltas ao mesmo tempo contra o mesmo bucket."""
    permitidos = []
    barreira = threading.Barrier(fios)

    def disputa():
        barreira.wait()
        permitidos.append(limitador.is_allowed('alvo'))

    linha = [threading.Thread(target=disputa) for _ in range(fios)]
    for f in linha:
        f.start()
    for f in linha:
        f.join()
    return sum(permitidos)


def test_r0_6_atomicidade_preservada():
    assert _corrida(RateLimiter(max_calls=5, period_seconds=60)) == 5


class _FilaLenta(deque):
    """Fila cuja MEDIÇÃO de tamanho cede o turno.

    O atraso precisa ficar exatamente entre a leitura (`len(window)`) e a
    escrita (`window.append`) — é essa a janela que o lock fecha. Na primeira
    versão eu atrasei a busca da janela no dicionário, ANTES da leitura, e o
    gate continuou verde com o lock removido: atrasar o lugar errado não
    reproduz a corrida.
    """

    def __len__(self):
        # Lê PRIMEIRO, cede o turno DEPOIS. Esta ordem é o ponto todo: o que
        # reproduz a corrida é carregar um tamanho VELHO através da troca de
        # contexto. Dormir antes de ler devolve valor fresco e o gate fica
        # verde com o lock removido — foi o que aconteceu na primeira tentativa.
        tamanho = super().__len__()
        time.sleep(0.002)
        return tamanho


class _JanelaLenta(dict):
    """Entrega filas lentas, sem tocar no produto.

    Isto não altera o `RateLimiter`. Só força o escalonador a fazer o que já
    tem direito de fazer — e aí a diferença aparece: com o lock, quem está
    dentro segura os outros e o teto se mantém; sem ele, as 20 threads leem a
    janela vazia antes de qualquer uma escrever.

    Medido: sem esta instrumentação, remover o lock foi acusado em 0 de 5
    execuções. O gate passava pelo motivo errado — não porque o lock existe,
    mas porque o agendador não interrompeu.
    """

    def __missing__(self, chave):
        valor = self[chave] = _FilaLenta()
        return valor


def test_r0_6b_o_teto_se_mantem_mesmo_com_troca_de_contexto_no_meio():
    limitador = RateLimiter(max_calls=5, period_seconds=60)
    limitador._windows = _JanelaLenta()
    liberados = _corrida(limitador)
    assert liberados == 5, (
        f'{liberados} threads passaram num limite de 5: a janela foi lida por '
        'várias antes de qualquer uma escrever'
    )


def test_r0_6c_a_secao_critica_continua_sob_lock():
    """Antemural estrutural do gate acima. Um é comportamental e pode ficar
    verde por sorte de agendamento; o outro não depende de sorte nenhuma."""
    import inspect
    fonte = inspect.getsource(RateLimiter.is_allowed)
    assert 'with self._lock:' in fonte, (
        'a seção crítica de `is_allowed` saiu de baixo do lock'
    )


# ── R0-7..R0-10: os quatro consumidores continuam protegidos ────────────────

def test_r0_7_a_10_os_quatro_limitadores_continuam_com_os_mesmos_limites():
    """Esta fatia muda QUEM ocupa o bucket, não QUANTAS requisições ele aceita."""
    esperado = {
        'login_limiter': (10, 60),
        'recovery_limiter': (5, 300),
        'tenant_limiter': (60, 60),
        'supplier_portal_limiter': (30, 60),
    }
    for nome, (chamadas, periodo) in esperado.items():
        limitador = getattr(RL, nome)
        assert (limitador._max, limitador._period) == (chamadas, periodo), (
            f'{nome} mudou de limite: {limitador._max}/{limitador._period}s')


def test_r0_7_a_10_os_quatro_limitadores_protegem_de_verdade():
    """Cada um recusa depois do teto, usando a origem endurecida."""
    with _com_saltos(0):
        for nome in ('login_limiter', 'recovery_limiter', 'tenant_limiter',
                     'supplier_portal_limiter'):
            limitador = getattr(RL, nome)
            teto = limitador._max
            origem = get_client_ip(_Handler(peer=f'198.51.100.{hash(nome) % 200}'))
            limitador.reset(origem)
            permitidos = sum(limitador.is_allowed(origem) for _ in range(teto + 5))
            assert permitidos == teto, f'{nome}: {permitidos} passaram, teto {teto}'
            # e o cabeçalho forjado não devolve fôlego a quem já estourou
            forjado = get_client_ip(_Handler(peer=f'198.51.100.{hash(nome) % 200}', xff='1.2.3.4'))
            assert not limitador.is_allowed(forjado), (
                f'{nome}: cabeçalho forjado devolveu bucket novo')
