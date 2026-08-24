"""O Motor B de reposição está CONGELADO (#271).

## Por que este gate existe

A auditoria da dívida de `replenishment._epi_levels` encontrou algo diferente
do que a issue registrava. Não há "a reposição automática usando o mínimo
errado": há **dois motores** do mesmo conceito.

- **Motor A — oficial, em produção, correto.**
  `modules.purchases.service.fetch_purchase_demands`, servido por
  `GET /api/purchase-demands`. Usa `classify_unit_epi_stock`, respeita
  `effective_minimum_stock` e ignora `near_minimum`/`disabled`.

- **Motor B — congelado.** `modules/stock/replenishment.py`, com ZERO
  chamadores fora dos testes. Ele é que lê o mínimo corporativo.

Como o Motor B nunca executa, ele não produz demanda errada hoje — e por isso
a correção dele não bloqueou a B3. Mas "não executa hoje" é uma propriedade
que se perde num único `import`, em silêncio, e aí a regra errada entra em
produção sem ninguém decidir isso.

**Este arquivo é a trava.** Ele não conserta a fórmula (isso é deliberado: ver
o docstring do módulo — mexer no mínimo sem decidir o `maximum_stock` criaria
um alvo híbrido Unidade × empresa). Ele apenas garante que o congelamento seja
uma decisão explícita, e não um acidente que ninguém percebeu.

Quando a issue de destino for resolvida, este gate falha pedindo atualização —
que é o objetivo.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Onde mora o código que roda em produção. `tests/` e `tests_postgres/` ficam
#: de fora de propósito: exercitar o módulo é justamente o que os mantém vivos
#: enquanto a decisão não vem.
ARVORES_DE_PRODUCAO = ('modules', 'core', 'epi_backend')
ARQUIVOS_DE_PRODUCAO = ('app.py', 'server_postgres.py')

MODULO = RAIZ / 'modules' / 'stock' / 'replenishment.py'
MOTOR_OFICIAL = RAIZ / 'modules' / 'purchases' / 'service.py'

#: O módulo importa a si mesmo indiretamente? Não — mas ele é o único arquivo
#: de produção autorizado a conter o próprio nome.
ALVO = 'modules.stock.replenishment'
ALVO_RELATIVO = 'stock.replenishment'


def _arquivos_de_producao():
    for arvore in ARVORES_DE_PRODUCAO:
        yield from sorted((RAIZ / arvore).rglob('*.py'))
    for nome in ARQUIVOS_DE_PRODUCAO:
        caminho = RAIZ / nome
        if caminho.exists():
            yield caminho


def _importa_o_motor_b(caminho: Path) -> bool:
    """Detecta import do Motor B por AST, não por regex.

    Regex acharia a menção dentro de comentário e de docstring — e este módulo
    é CITADO de propósito em vários lugares para explicar o congelamento.
    Confundir a prosa com o import transformaria a documentação em violação.
    """
    try:
        arvore = ast.parse(caminho.read_text(encoding='utf-8'))
    except SyntaxError:  # pragma: no cover - arquivo quebrado é problema de outro gate
        return False
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            if any(a.name.endswith(ALVO_RELATIVO) or a.name == ALVO for a in no.names):
                return True
        elif isinstance(no, ast.ImportFrom):
            modulo = no.module or ''
            if modulo.endswith(ALVO_RELATIVO) or modulo == ALVO:
                return True
            # `from modules.stock import replenishment`
            if modulo.endswith('modules.stock') or modulo == 'modules.stock':
                if any(a.name == 'replenishment' for a in no.names):
                    return True
    return False


def test_nenhum_codigo_de_producao_importa_o_motor_b():
    """A trava principal.

    Um chamador novo aqui significa que a reposição pelo mínimo CORPORATIVO
    passou a executar — sem que a decisão sobre `maximum_stock`, sobre o
    `stock_alert_enabled` e sobre a duplicação de motor tivesse sido tomada.
    """
    infratores = [
        str(c.relative_to(RAIZ))
        for c in _arquivos_de_producao()
        if c != MODULO and _importa_o_motor_b(c)
    ]
    assert not infratores, (
        'modules/stock/replenishment.py está CONGELADO e ganhou chamador de '
        f'produção em: {infratores}. Antes de ligar este motor, resolva a issue '
        'de destino dele — ela cobre a duplicação com fetch_purchase_demands, o '
        'mínimo corporativo em _epi_levels, o stock_alert_enabled ignorado e o '
        'maximum_stock sem equivalente por Unidade.'
    )


def test_o_modulo_continua_existindo_e_testado():
    """Congelar não é apagar.

    O Motor B tem capacidades que o oficial não tem — antiduplicidade (§4.2) e
    a corrente `necessidade → requisição` (§3.8). Elas são o motivo de o
    módulo não ter sido removido, e a suíte dele é o que as mantém
    demonstráveis para quando a decisão vier.
    """
    assert MODULO.exists(), 'o Motor B foi removido sem fechar a issue de destino'
    suite = RAIZ / 'tests' / 'test_stock_replenishment.py'
    assert suite.exists(), 'a suíte do Motor B sumiu — as capacidades dele ficam sem prova'


def test_o_congelamento_esta_documentado_no_proprio_modulo():
    """O aviso mora no arquivo, não só aqui.

    Quem abre `replenishment.py` para usá-lo precisa ler o congelamento ANTES
    de escrever o import — depender de alguém rodar a suíte para descobrir
    seria tarde demais.
    """
    fonte = MODULO.read_text(encoding='utf-8')
    assert 'MÓDULO CONGELADO' in fonte
    assert 'fetch_purchase_demands' in fonte, \
        'o aviso precisa apontar para o motor oficial'


def test_o_motor_oficial_esta_marcado_como_fonte_operacional():
    """E o inverso: quem chega pelo motor oficial precisa saber que o outro
    existe e está congelado, senão a duplicação é redescoberta do zero."""
    fonte = MOTOR_OFICIAL.read_text(encoding='utf-8')
    assert 'FONTE OPERACIONAL OFICIAL' in fonte
    assert 'replenishment.py' in fonte and 'CONGELADO' in fonte


def test_as_quatro_divergencias_seguem_registradas():
    """A issue de destino não pode nascer sem os pontos que a motivam.

    Se alguém corrigir uma delas isoladamente — o caso mais provável é migrar
    só o mínimo — este teste falha pedindo que o registro seja atualizado
    junto, em vez de deixar o docstring descrevendo um módulo que já mudou.
    """
    fonte = MODULO.read_text(encoding='utf-8')
    for ancora in (
        'epis.minimum_stock',        # 1. mínimo corporativo
        'stock_alert_enabled',       # 2. toggle da B2-a ignorado
        'maximum_stock',             # 3. sem equivalente por Unidade
        'antiduplicidade',           # 4. capacidade exclusiva do Motor B
    ):
        assert ancora in fonte, (
            f'a divergência {ancora!r} sumiu do registro de congelamento; '
            'atualize o docstring do módulo E a issue de destino'
        )


def test_a_formula_do_motor_b_nao_foi_alterada_no_congelamento():
    """Congelar é NÃO mexer.

    Corrigir `_epi_levels` para o mínimo por Unidade sem decidir o
    `maximum_stock` produziria `target = maximum_corporativo or minimo_da_unidade`
    — uma regra híbrida, dentro de código que nem executa. A decisão de
    escopo do máximo precisa vir antes; até lá a assinatura antiga é a prova
    de que ninguém mexeu pela metade.
    """
    fonte = MODULO.read_text(encoding='utf-8')
    assert 'def _epi_levels(connection, epi_id)' in fonte, (
        '_epi_levels mudou de assinatura. Se a migração foi feita, remova este '
        'teste junto com o congelamento e atualize a issue de destino.'
    )
    # A ausência da resolução oficial é o estado esperado — mas a checagem é
    # por AST, e não por texto: o docstring do congelamento CITA
    # `classify_unit_epi_stock` de propósito, para explicar o que o motor
    # oficial faz e este não. Procurar a string transformaria a própria
    # documentação em violação (foi o que aconteceu na primeira versão deste
    # teste).
    usados = _nomes_invocados_ou_importados(MODULO)
    for oficial in ('classify_unit_epi_stock', 'resolve_unit_minimum_stock'):
        assert oficial not in usados, (
            f'o módulo passou a usar {oficial} — o congelamento acabou sem que a '
            'issue de destino fosse fechada. Se a migração é intencional, '
            'remova este gate junto.'
        )


def _nomes_invocados_ou_importados(caminho: Path) -> set[str]:
    """Nomes que o módulo de fato CHAMA ou IMPORTA — prosa não conta."""
    arvore = ast.parse(caminho.read_text(encoding='utf-8'))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.Call):
            alvo = no.func
            if isinstance(alvo, ast.Name):
                nomes.add(alvo.id)
            elif isinstance(alvo, ast.Attribute):
                nomes.add(alvo.attr)
    return nomes
