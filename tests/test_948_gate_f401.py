"""#948, fatia 1 — `tests/` e `scripts/` param de crescer dívida de imports ociosos.

O defeito era de cobertura, não de código: o job `Lint (ruff)` rodava só sobre
`epi_backend modules app.py`, então nada lintava `tests/` e `scripts/`. Quem
achava um import ocioso era o CodeQL, DEPOIS do push, como comentário de
review. Aconteceu duas vezes em fatias consecutivas da #271 — padrão, não
descuido.

Esta fatia não tenta zerar os ~300 achados de outras regras. Ela torna
bloqueante **uma** propriedade já zerada, e só ela:

    F401 em tests/ + scripts/ == 0

O mecanismo é seleção de regra, nunca supressão de achado. Não há arquivo de
baseline, `--exit-zero` nem allowlist: uma regra está no gate a zero, ou não
está no gate. "No gate acima de N" seria um baseline artificial, por onde
dívida nova entra por baixo do número.

Sobre a sabotagem: ela planta o import ocioso numa CÓPIA em diretório
temporário, nunca na árvore versionada. Uma contraprova que commitasse o
defeito para provar que o detector o vê violaria a regra que impõe.
"""

import pathlib
import re
import shutil
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / '.github' / 'workflows' / 'backend-ci.yml'

#: A seleção exata do gate. Mudar isto é mudar o contrato da fatia 1.
SELECAO = ('--select', 'F401')
ALVOS = ('tests', 'scripts')


def _sem_comentarios(texto: str) -> str:
    """YAML sem `#`.

    Necessário porque os comentários do próprio passo citam `continue-on-error`
    e `--exit-zero` justamente para dizer que NÃO estão ali. Um matcher por
    substring reprovaria a documentação da regra que ele existe para impor —
    o mesmo cuidado que `_constantes_de_codigo` toma na #313.
    """
    return '\n'.join(
        linha.split('#', 1)[0].rstrip() if '#' in linha else linha
        for linha in texto.splitlines())


def _passo_do_gate() -> str:
    """O bloco YAML do passo bloqueante, delimitado por indentação.

    Recortado por indentação e não por regex sobre o arquivo inteiro porque o
    job tem outro passo de ruff — o amplo, que CONTINUA não bloqueante — e um
    matcher frouxo confundiria os dois, aprovando o gate ao ler o passo errado.
    """
    linhas = WORKFLOW.read_text(encoding='utf-8').splitlines()
    inicio = next(
        (i for i, linha in enumerate(linhas)
         if linha.strip().startswith('- name:') and 'F401' in linha), None)
    assert inicio is not None, 'passo bloqueante de F401 ausente do workflow'
    recuo = len(linhas[inicio]) - len(linhas[inicio].lstrip())
    fim = inicio + 1
    while fim < len(linhas):
        atual = linhas[fim]
        if atual.strip() and (len(atual) - len(atual.lstrip())) <= recuo:
            break
        fim += 1
    return _sem_comentarios('\n'.join(linhas[inicio:fim]))


def _ruff(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m', 'ruff', 'check', *args],
        cwd=RAIZ, capture_output=True, text=True, check=False)


# ── O pin de versão ──────────────────────────────────────────────────────────

def test_o_ruff_esta_pinado_em_versao_exata():
    """Sem pin, o baseline se move a cada release e o gate vira ruído.

    Medido: a árvore de 24/08 tinha 56 achados com o ruff da época e tem 310
    com o 0.16.5. Um gate bloqueante sobre baseline móvel fica vermelho em
    código que ninguém tocou, e o reflexo é devolver o `continue-on-error`.
    """
    texto = _sem_comentarios(WORKFLOW.read_text(encoding='utf-8'))
    instalacoes = re.findall(r'pip install ruff(\S*)', texto)
    assert instalacoes, 'nenhuma instalação de ruff no workflow'
    for sufixo in instalacoes:
        assert re.fullmatch(r'==\d+\.\d+\.\d+', sufixo), (
            f'ruff instalado sem versão exata: `pip install ruff{sufixo}`. '
            f'Esperado `ruff==X.Y.Z`.')


# ── A forma do gate ──────────────────────────────────────────────────────────

def test_o_gate_cobre_tests_e_scripts_com_a_selecao_certa():
    passo = _passo_do_gate()
    for alvo in ALVOS:
        assert re.search(rf'\bruff check\b.*\b{alvo}\b', passo), \
            f'`{alvo}` fora do gate bloqueante'
    assert ' '.join(SELECAO) in passo, \
        f'seleção do gate mudou; esperado `{" ".join(SELECAO)}`'


def test_o_gate_e_bloqueante_de_verdade():
    """As três formas de um gate existir e não reprovar nada."""
    passo = _passo_do_gate()
    assert 'continue-on-error' not in passo, \
        'o gate de F401 ganhou `continue-on-error`: existe e não reprova'
    assert '--exit-zero' not in passo, \
        '`--exit-zero` no gate de F401: sempre verde'
    for suprimente in ('--statistics', '--ignore', '--exclude', 'baseline'):
        assert suprimente not in passo, \
            f'`{suprimente}` no gate: supressão em lugar de seleção'


def test_o_lint_amplo_continua_separado_e_nao_bloqueante():
    """A fatia 1 não torna bloqueante o que ainda tem ~300 achados.

    Contraprova do gate anterior: se `continue-on-error` tivesse sumido do
    workflow inteiro em vez de apenas não estar no passo novo, o teste acima
    passaria por motivo errado.
    """
    texto = _sem_comentarios(WORKFLOW.read_text(encoding='utf-8'))
    assert 'continue-on-error: true' in texto, \
        'o lint amplo perdeu o `continue-on-error`: fatia 2 entrou de carona'
    assert 'ruff check epi_backend modules app.py' in texto, \
        'o lint amplo desapareceu'


# ── O baseline, e a prova de que ele não é vácuo ─────────────────────────────

def test_o_baseline_de_f401_e_zero():
    resultado = _ruff(*ALVOS, *SELECAO)
    assert resultado.returncode == 0, (
        'F401 em tests/ ou scripts/ — a dívida que a fatia 1 zerou voltou:\n'
        + resultado.stdout)


def test_a_sabotagem_deixa_o_gate_vermelho(tmp_path):
    """Planta um import ocioso numa CÓPIA e exige que o gate reprove.

    Sem isto, `returncode == 0` no teste anterior é indistinguível de um ruff
    que não roda, de um alvo inexistente ou de uma seleção que não casa nada.
    """
    original = RAIZ / 'tests' / 'test_948_gate_f401.py'
    copia = tmp_path / 'test_sabotagem.py'
    shutil.copy(original, copia)

    limpo = _ruff(str(tmp_path), *SELECAO)
    assert limpo.returncode == 0, \
        f'a cópia já nasceu suja — sabotagem inconclusiva:\n{limpo.stdout}'

    copia.write_text('import json\n' + copia.read_text(encoding='utf-8'),
                     encoding='utf-8')
    sabotado = _ruff(str(tmp_path), *SELECAO)
    assert sabotado.returncode != 0, \
        'o gate aprovou um import ocioso plantado — regra inútil'
    assert 'F401' in sabotado.stdout, \
        f'reprovou por outro motivo que não F401:\n{sabotado.stdout}'

    copia.write_text(copia.read_text(encoding='utf-8').replace('import json\n', '', 1),
                     encoding='utf-8')
    restaurado = _ruff(str(tmp_path), *SELECAO)
    assert restaurado.returncode == 0, \
        f'o gate ficou vermelho depois de restaurar:\n{restaurado.stdout}'


def test_a_arvore_versionada_nao_tem_a_sabotagem():
    """A contraprova acima não pode deixar dívida commitada."""
    resultado = _ruff('tests/test_948_gate_f401.py', *SELECAO)
    assert resultado.returncode == 0, \
        'o próprio arquivo de gate tem import ocioso versionado'
