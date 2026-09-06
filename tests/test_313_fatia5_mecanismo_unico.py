"""Fatia 5 da #313 — usuário e senha são o ÚNICO mecanismo de autenticação.

As fatias 1 a 4 construíram o caminho novo e provaram que ele funciona nos dois
deployments. Esta fatia remove o antigo. O risco muda de lugar junto: deixa de
ser "o modo novo funciona?" e passa a ser "alguém reintroduz o modo velho sem
que ninguém perceba?".

Por isso os gates aqui são de NÃO-EXISTÊNCIA, e cada um vem com a sabotagem que
prova que ele acusaria a volta. Um gate de ausência que não reprova a presença
é indistinguível de um gate quebrado — ele passa exatamente igual nos dois
mundos, e o dia em que passar a mentir ninguém descobre.

Nota sobre o nome do secret removido: ele NÃO aparece escrito em lugar nenhum
deste arquivo. O gate 1 exige zero ocorrências versionadas, e uma fixture que
carregasse o literal para provar a detecção violaria a própria regra que impõe.
As sabotagens montam o nome em tempo de execução, por concatenação.
"""

import ast
import pathlib
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / 'scripts' / 'certificar_deployment.py'
WORKFLOW = RAIZ / '.github' / 'workflows' / 'certificacao-271.yml'

from tests.test_313_certificador_autentica import _instrumentar, _modulo, _Rede

#: Montado em pedaços de propósito — ver a nota do docstring. O padrão casa
#: tanto os nomes concretos quanto a forma genérica usada em prosa.
_PREFIXO = 'EPI_CERT_'
_SUFIXO = 'TOKEN'
_PADRAO = _PREFIXO + r'[A-Z0-9_*]*' + _SUFIXO

_NOME_CORP = _PREFIXO + 'CORP_' + _SUFIXO
_NOME_SAAS = _PREFIXO + 'SAAS_' + _SUFIXO


# ── Gate 1: zero referências versionadas ao secret de token estático ─────────

def _ocorrencias(pares) -> list:
    """Onde `EPI_CERT_<algo>_TOKEN` aparece, dado (caminho, conteúdo).

    Função pura, e é isso que torna a sabotagem possível sem sujar o
    repositório: o gate real recebe os arquivos versionados, a contraprova
    recebe conteúdo montado em memória. Os dois exercitam ESTE código.
    """
    import re
    achados = []
    for caminho, texto in pares:
        for linha_num, linha in enumerate(texto.splitlines(), 1):
            if re.search(_PADRAO, linha):
                achados.append(f'{caminho}:{linha_num}')
    return achados


def _pares_versionados():
    """Só o que está sob controle de versão.

    `git ls-files` e não uma varredura do disco: `__pycache__` guarda o
    bytecode da versão anterior do certificador, com o nome do secret ainda
    dentro. Reprovar por causa de um artefato de build seria ruído, e o
    requisito é sobre o que está COMMITADO.
    """
    saida = subprocess.run(
        ['git', 'ls-files', '-z'], cwd=RAIZ, capture_output=True, check=True)
    for nome in saida.stdout.decode('utf-8', errors='replace').split('\0'):
        if not nome:
            continue
        caminho = RAIZ / nome
        try:
            yield nome, caminho.read_text(encoding='utf-8', errors='ignore')
        except (OSError, ValueError):
            continue


def test_nenhuma_referencia_versionada_ao_token_estatico():
    achados = _ocorrencias(_pares_versionados())
    assert achados == [], \
        f'o secret de token estático voltou ao repositório: {achados}'


def test_o_detector_de_referencia_nao_e_vacuo():
    """Contraprova do gate 1, sem deixar o literal commitado."""
    for nome in (_NOME_CORP, _NOME_SAAS, _PREFIXO + '*_' + _SUFIXO):
        forjado = [('memoria.yml', f'          {nome}: ' + '${{ secrets.X }}')]
        assert _ocorrencias(forjado), f'o detector não veria {nome!r} — regra inútil'


# ── Gate 3: `MODO_LEGADO` não existe ─────────────────────────────────────────

def _cita_modo_legado(fonte: str) -> bool:
    return any(
        getattr(no, 'id', '') == 'MODO_LEGADO' or getattr(no, 'attr', '') == 'MODO_LEGADO'
        for no in ast.walk(ast.parse(fonte)))


def test_o_modo_legado_nao_existe():
    m = _modulo()
    assert not hasattr(m, 'MODO_LEGADO')
    assert not _cita_modo_legado(SCRIPT.read_text(encoding='utf-8'))


def test_o_detector_de_modo_legado_nao_e_vacuo():
    """Contraprova do gate 3."""
    sabotado = SCRIPT.read_text(encoding='utf-8').replace(
        "MODO_NOVO = 'credenciais'",
        "MODO_NOVO = 'credenciais'\nMODO_LEGADO = 'token_estatico'", 1)
    assert _cita_modo_legado(sabotado), 'o detector não veria o modo legado voltar'


# ── Gate 4: nenhum fallback para credencial alternativa ──────────────────────

def _funcao(fonte: str, nome: str):
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    raise AssertionError(f'`{nome}` não encontrada — matcher quebrado')


def _fallbacks(fonte: str) -> list:
    """Motivos pelos quais a credencial do smoke poderia não vir do login.

    Três formas, porque `login() or TOKEN` é só a mais óbvia: um `or` na
    função, uma leitura de ambiente com `TOKEN` no nome, ou uma atribuição a
    `token` cuja origem não seja `_login`.
    """
    motivos = []
    alvo = _funcao(fonte, 'certificar_api')

    for no in ast.walk(alvo):
        # `BoolOp` que TOCA a credencial, não qualquer `or` da função: o
        # `body.get('items') or []` do smoke é um default de lista e não tem
        # nada a ver com autenticação. Um gate que reprovasse os dois obrigaria
        # a reescrever código alheio para passar, e quem reescreve para passar
        # acaba afrouxando o gate.
        if isinstance(no, ast.BoolOp) and any(
                getattr(f, 'id', '') in ('token', '_login')
                for f in ast.walk(no)
                if isinstance(f, (ast.Name, ast.Attribute))):
            motivos.append('expressão booleana sobre a credencial em '
                           '`certificar_api`: possível `_login(...) or <credencial>`')

    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) \
                and _SUFIXO in no.value.upper() and no.value.upper().startswith(_PREFIXO):
            motivos.append(f'literal de credencial antiga no código: {no.value!r}')

    for no in ast.walk(alvo):
        origens = []
        if isinstance(no, ast.Assign):
            nomes = {a.id for a in ast.walk(ast.Tuple(elts=no.targets))
                     if isinstance(a, ast.Name)}
            if 'token' in nomes:
                origens.append(no.value)
        for valor in origens:
            vindo_do_login = (
                isinstance(valor, ast.Call)
                and getattr(valor.func, 'id', '') == '_login')
            inicializacao = isinstance(valor, ast.Constant) and valor.value == ''
            if not (vindo_do_login or inicializacao):
                motivos.append('`token` recebeu valor de origem que não é `_login`')
    return motivos


def test_nao_ha_fallback_de_credencial():
    motivos = _fallbacks(SCRIPT.read_text(encoding='utf-8'))
    assert motivos == [], f'fallback de credencial no certificador: {motivos}'


@pytest.mark.parametrize('nome', ['or_ambiente', 'atribuicao_direta'])
def test_o_detector_de_fallback_nao_e_vacuo(nome):
    """Contraprova do gate 4, com o nome do secret montado em memória."""
    fonte = SCRIPT.read_text(encoding='utf-8')
    ancora = '    token, erro_login = _login(raiz, usuario, senha)'
    assert ancora in fonte, 'MUTACAO NAO APLICOU: âncora ausente'
    if nome == 'or_ambiente':
        enxerto = (f"{ancora}\n    token = token or "
                   f"os.environ.get({_NOME_CORP!r}, '')")
    else:
        enxerto = f"{ancora}\n    token = os.environ.get({_NOME_SAAS!r}, '')"
    assert _fallbacks(fonte.replace(ancora, enxerto, 1)), \
        f'o detector não veria o fallback {nome!r} — regra inútil'


# ── Gate 5: sem USER/PASSWORD nada é sondado, e o veredito é código 2 ────────

def _ambiente_sem_credencial(monkeypatch):
    """URLs de API presentes, credenciais ausentes, tokens antigos PRESENTES.

    O ambiente é montado com os dois nomes de secret antigos definidos e com um
    valor que parece um JWT. É o caso perigoso: se sobrasse qualquer leitura
    deles, este seria o teste que passaria a certificar.

    `EPI_CERT_SAAS_WEB_URL` fica de fora porque o Flutter Web não autentica —
    ele sondaria de qualquer jeito e poluiria a contagem de requisições.
    """
    for nome in ('EPI_CERT_CORP_URL', 'EPI_CERT_SAAS_API_URL'):
        monkeypatch.setenv(nome, 'https://exemplo-invalido')
    monkeypatch.delenv('EPI_CERT_SAAS_WEB_URL', raising=False)
    for nome in ('EPI_CERT_CORP_USER', 'EPI_CERT_CORP_PASSWORD',
                 'EPI_CERT_SAAS_USER', 'EPI_CERT_SAAS_PASSWORD'):
        monkeypatch.delenv(nome, raising=False)
    for nome in (_NOME_CORP, _NOME_SAAS):
        monkeypatch.setenv(nome, 'eyJhbGciOiJIUzI1NiJ9.forjado.assinatura')


def test_sem_credencial_o_veredito_e_codigo_2_e_zero_requisicoes(monkeypatch):
    _ambiente_sem_credencial(monkeypatch)
    m = _instrumentar(_modulo(), rede := _Rede([]))
    codigo = m.main()
    assert codigo == 2, \
        f'ausência de credencial devolveu {codigo}, não o código 2 de NOT CERTIFIED'
    assert not rede.gets and not rede.logins, \
        f'houve requisição sem credencial: gets={rede.gets} logins={rede.logins}'


def test_o_mesmo_arranjo_com_credencial_de_fato_sonda(monkeypatch):
    """Contraprova do gate 5: o zero acima vem da regra, não de um arnês morto."""
    _ambiente_sem_credencial(monkeypatch)
    for nome in ('EPI_CERT_CORP_USER', 'EPI_CERT_CORP_PASSWORD',
                 'EPI_CERT_SAAS_USER', 'EPI_CERT_SAAS_PASSWORD'):
        monkeypatch.setenv(nome, 'valor')
    m = _instrumentar(_modulo(), rede := _Rede([(401, {}, {})] * 40))
    m._validar_identidade = lambda raiz, token: 'identidade forjada'
    m.main()
    assert rede.gets, 'com credencial presente o arnês também não sondou — arnês morto'


# ── Gate 7: os quatro USER/PASSWORD continuam no workflow ────────────────────

_OBRIGATORIOS = ('EPI_CERT_CORP_USER', 'EPI_CERT_CORP_PASSWORD',
                 'EPI_CERT_SAAS_USER', 'EPI_CERT_SAAS_PASSWORD')


def _faltando_no_workflow(texto: str) -> list:
    return [nome for nome in _OBRIGATORIOS
            if f'{nome}: ${{{{ secrets.{nome} }}}}' not in texto]


def test_o_workflow_exporta_as_quatro_credenciais():
    """Sem elas, TODO deployment sairia `NOT CERTIFIED` — honesto e inútil."""
    texto = WORKFLOW.read_text(encoding='utf-8')
    assert _faltando_no_workflow(texto) == [], \
        f'credencial ausente do workflow: {_faltando_no_workflow(texto)}'
    assert _ocorrencias([('certificacao-271.yml', texto)]) == [], \
        'o workflow voltou a exportar o secret de token estático'


def test_o_detector_do_workflow_nao_e_vacuo():
    """Contraprova do gate 7."""
    texto = WORKFLOW.read_text(encoding='utf-8')
    for nome in _OBRIGATORIOS:
        mutilado = texto.replace(f'{nome}: ${{{{ secrets.{nome} }}}}', '', 1)
        assert _faltando_no_workflow(mutilado) == [nome], \
            f'o detector não veria a remoção de {nome}'
