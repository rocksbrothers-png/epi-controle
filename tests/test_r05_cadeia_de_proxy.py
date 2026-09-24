"""R0.5 — gates do contrato FECHADO da cadeia de proxy.

A R0 deixou `RATE_LIMIT_TRUSTED_PROXY_HOPS` com padrão `0` porque não havia
como comprovar outro número. A R0.5 mediu em produção, com três controles e
três repetições cada, e o contrato fechou em **3**.

`docs/R05_CADEIA_DE_PROXY.md` registra a evidência. Este arquivo trava as sete
regressões que o fechamento cria ou mantém:

- `R05-1`  o contrato continua legível por máquina
- `R05-2`  paridade Corporate × SaaS do contrato e do limitador
- `R05-3`  o valor do deployment bate com o contrato, e o modelo genérico
           nunca carrega valor topológico
- `R05-4`  o contrato bate com a evidência medida
- `R05-5`  a sonda temporária saiu, e não volta
- `R05-6`  `PROXY_CHAIN_PROBE_KEY` não é dependência de nada
- `R05-7`  a origem falha fechada quando a configuração é inválida
- `R05-8`  a proteção anti-spoofing da R0 continua de pé

Os gates `R05-3`, `R05-5` e `R05-6` mudaram de exigência sozinhos quando o
contrato passou de `INDETERMINADO` para `DETERMINADO` — era para isso que a
condicional existia. Eles continuam condicionais: se uma remedição reabrir o
contrato, a exigência se inverte de novo sem ninguém lembrar de mexer aqui.
"""

import hashlib
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import core.rate_limit as RL

#: Vocabulário do modelo de borda. Declarado aqui, e não lido da sonda, porque
#: a sonda não existe mais — o contrato continua precisando ser verificável.
VEREDITOS_CONHECIDOS = (
    'ANEXA', 'SOBRESCREVE', 'HIGIENIZA', 'PASSA_DIRETO', 'INDETERMINADO',
)

#: Só três modelos fecham contrato. `INDETERMINADO` nunca foi aceitável, e
#: `SOBRESCREVE` deixou de ser quando um contraexemplo mostrou que forma
#: constante não prova que o elemento restante seja o cliente.
MODELOS_QUE_FECHAM = ('ANEXA', 'PASSA_DIRETO', 'HIGIENIZA')

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / 'docs' / 'R05_CADEIA_DE_PROXY.md'
ENV_EXEMPLO = RAIZ / 'env.example'
RENDER = RAIZ / 'render.yaml'
SONDA_MODULO = RAIZ / 'epi_backend' / 'proxy_chain_probe.py'
SCRIPT_SONDA = RAIZ / 'scripts' / 'certificar_cadeia_de_proxy.py'
ROTAS_AUTH = RAIZ / 'modules' / 'auth' / 'routes.py'
LIMITADOR = RAIZ / 'core' / 'rate_limit.py'

INICIO = '<!-- CONTRATO-R05-INICIO -->'
FIM = '<!-- CONTRATO-R05-FIM -->'

VARIAVEL = 'RATE_LIMIT_TRUSTED_PROXY_HOPS'
CHAVE_DA_SONDA = 'PROXY_CHAIN_PROBE_KEY'
ROTA_DA_SONDA = 'proxy-chain-diagnostics'

# Digesto do bloco de contrato. Os dois repositórios carregam a MESMA
# constante, então editar o contrato de um lado só deixa aquele lado vermelho.
# Limitação honesta, a mesma dos outros digestos de paridade do projeto: pega
# edição unilateral, não pega os dois editando igual e errado ao mesmo tempo.
DIGESTO_CONTRATO_R05 = 'eb2f9b9c323f9077b53c57fb003708676ce945cfa5a643ce698b13c516f44fd6'

# Digesto de `core/rate_limit.py`. O contrato é sobre um número, mas quem lê
# esse número é este módulo: se um repositório mexer nele e o outro não, a
# cadeia declarada deixa de significar a mesma coisa nos dois.
DIGESTO_LIMITADOR_R05 = 'aab6c8acb2212232c3558887eac85f8061033e323baeb7ee59592a9903f0237e'


def _sem_comentarios(fonte: str) -> str:
    """Tira linhas de comentário antes de procurar estrutura.

    Convenção que o projeto já usa em `tests/test_343_f2_teardown_logout.py`:
    sem ela, um gate reprova pelo comentário que explica o que ele proíbe.
    """
    return '\n'.join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith('#')
    )


def _bloco_do_contrato() -> str:
    texto = CONTRATO.read_text(encoding='utf-8')
    assert INICIO in texto and FIM in texto, 'marcadores do contrato sumiram'
    return texto.split(INICIO, 1)[1].split(FIM, 1)[0].strip()


def _campos_do_contrato() -> dict:
    campos = {}
    for linha in _bloco_do_contrato().splitlines():
        if ':' in linha:
            chave, valor = linha.split(':', 1)
            campos[chave.strip()] = valor.strip()
    return campos


def _determinado() -> bool:
    return _campos_do_contrato().get('ESTADO-DA-CADEIA') == 'DETERMINADO'


CONTRATO_R05B = RAIZ / 'docs' / 'R05B_IDENTIDADE_DA_ORIGEM.md'

#: Superfícies que a R0.5B declara como autorizadas a ler a chave enquanto a
#: certificação de identidade estiver aberta. Lista fechada: qualquer leitura
#: fora dela é regressão, mesmo com a fatia aberta.
SUPERFICIES_R05B = (
    'epi_backend/proxy_identity_probe.py',
    'docs/R05B_IDENTIDADE_DA_ORIGEM.md',
    'tests/test_r05b_identidade_da_origem.py',
)


def _identidade_em_aberto() -> bool:
    """A R0.5B ainda está certificando identidade?

    Enquanto estiver, a sonda dela pode existir e ler a chave — e só ela. Ver
    `docs/R05B_IDENTIDADE_DA_ORIGEM.md` §1.
    """
    if not CONTRATO_R05B.exists():
        return False
    texto = CONTRATO_R05B.read_text(encoding='utf-8')
    if 'CONTRATO-R05B-INICIO' not in texto:
        return False
    bloco = texto.split('<!-- CONTRATO-R05B-INICIO -->', 1)[1]
    bloco = bloco.split('<!-- CONTRATO-R05B-FIM -->', 1)[0]
    for linha in bloco.splitlines():
        if linha.strip().startswith('ESTADO-DA-IDENTIDADE:'):
            return linha.split(':', 1)[1].strip() == 'INDETERMINADO'
    return False


def _valores_declarados(texto: str) -> list:
    """Extrai os valores de `RATE_LIMIT_TRUSTED_PROXY_HOPS` nas DUAS formas.

    `env.example` usa `VARIAVEL=3`. O `render.yaml` usa a estrutura de lista que
    o blueprint da Render consome:

        - key: RATE_LIMIT_TRUSTED_PROXY_HOPS
          value: "3"

    Procurar a variável e um número na MESMA linha reprovaria a declaração
    correta do blueprint — e empurraria quem tentasse satisfazer o gate a
    escrever um mapeamento inline que a Render não lê.
    """
    valores = []
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        casou = re.match(rf'\s*{VARIAVEL}\s*=\s*"?(\d+)"?\s*$', linha)
        if casou:
            valores.append(casou.group(1))
            continue
        if not re.search(rf'key:\s*{VARIAVEL}\s*$', linha):
            continue
        for seguinte in linhas[i + 1:]:
            if re.match(r'\s*-\s', seguinte):
                break  # começou outra entrada de envVars sem declarar valor
            casou = re.match(r'\s*value:\s*"?(\d+)"?\s*$', seguinte)
            if casou:
                valores.append(casou.group(1))
                break
    return valores


def _contribuicoes_medidas() -> list:
    """Lê a contribuição da borda na tabela de medição do documento.

    A tabela do §2 tem a contribuição na última coluna, em negrito. Ler dali
    amarra o número do contrato à evidência registrada, em vez de deixar os
    dois como declarações independentes que podem divergir em silêncio.
    """
    texto = CONTRATO.read_text(encoding='utf-8')
    contribuicoes = []
    for linha in texto.splitlines():
        if not linha.startswith('| **'):
            continue
        celulas = [c.strip() for c in linha.strip('|').split('|')]
        ultima = celulas[-1]
        casou = re.fullmatch(r'\*\*(\d+)\*\*', ultima)
        if casou:
            contribuicoes.append(int(casou.group(1)))
    return contribuicoes


# ── R05-1: o contrato continua legível por máquina ──────────────────────────

def test_r05_1_o_contrato_e_legivel_por_maquina():
    campos = _campos_do_contrato()
    for obrigatorio in ('ESTADO-DA-CADEIA', 'SALTOS-CONFIAVEIS',
                        'MODELO-DA-BORDA', 'ORIGENS-CORROBORADAS', 'EVIDENCIA'):
        assert obrigatorio in campos, f'contrato sem o campo {obrigatorio}'
    assert campos['ESTADO-DA-CADEIA'] in ('INDETERMINADO', 'DETERMINADO'), \
        'ESTADO-DA-CADEIA só admite INDETERMINADO ou DETERMINADO'


# ── R05-2: paridade Corporate × SaaS ────────────────────────────────────────

def test_r05_2_o_contrato_e_identico_nos_dois_repositorios():
    """Nenhum dos dois repositórios enxerga o outro. Compara com o digesto que
    os dois carregam igual, o que reprova quem editar de um lado só."""
    atual = hashlib.sha256(_bloco_do_contrato().encode('utf-8')).hexdigest()
    assert atual == DIGESTO_CONTRATO_R05, (
        'o bloco de contrato mudou sem o digesto ser recalculado nos DOIS '
        f'repositórios. Atual: {atual}'
    )


def test_r05_2b_o_limitador_e_identico_nos_dois_repositorios():
    """O contrato é sobre um número; quem lê o número é `core/rate_limit.py`.
    Se um repositório mexer nele e o outro não, `3` deixa de significar a mesma
    coisa nos dois — e o gate do contrato, que olha só o documento, não veria."""
    atual = hashlib.sha256(LIMITADOR.read_bytes()).hexdigest()
    assert atual == DIGESTO_LIMITADOR_R05, (
        'core/rate_limit.py divergiu entre os repositórios, ou mudou sem o '
        f'digesto ser recalculado nos dois. Atual: {atual}'
    )


# ── R05-3: o valor do deployment bate com o contrato ────────────────────────

def test_r05_3_o_render_declara_exatamente_o_valor_do_contrato():
    """Condicional: enquanto INDETERMINADO, declarar um número é o erro; depois
    de DETERMINADO, NÃO declarar é o erro.

    Vale para `render.yaml`, que é específico da topologia medida. O
    `env.example` tem regra própria, no gate seguinte — e mais estrita.
    """
    campos = _campos_do_contrato()

    if not _determinado():
        for caminho in (ENV_EXEMPLO, RENDER):
            if caminho.exists():
                assert VARIAVEL not in caminho.read_text(encoding='utf-8'), (
                    f'{caminho.name} declara {VARIAVEL} com a cadeia ainda '
                    'INDETERMINADA — é exatamente o palpite que a R0 recusou'
                )
        return

    esperado = campos['SALTOS-CONFIAVEIS']
    assert RENDER.exists(), 'render.yaml sumiu'
    valores = _valores_declarados(RENDER.read_text(encoding='utf-8'))
    assert valores, (
        f'contrato DETERMINADO e render.yaml não declara {VARIAVEL}. '
        'Deployment sem o valor volta ao padrão 0 e colapsa as origens'
    )
    for valor in valores:
        assert valor == esperado, (
            f'render.yaml declara {VARIAVEL}={valor} e o contrato diz '
            f'{esperado} — documentação e deployment discordam'
        )


def test_r05_3b_o_modelo_generico_nunca_carrega_valor_topologico():
    """`env.example` é modelo para QUALQUER implantação, e
    `spec/09-deployment.md` manda copiá-lo para `.env`.

    A cadeia que torna isso perigoso foi medida: `app.py` importa
    `epi_backend.config` — que chama `load_dotenv()` — antes de importar
    `core.rate_limit`, então o que está no `.env` vira a fronteira de confiança
    de quem seguiu o procedimento. Num ambiente sem proxy, declarar 3 ali deixa
    o cliente mandar três elementos, alcançar o comprimento exigido e receber
    `cadeia[-3]`, que é o primeiro — escrito por ele. Baldes ilimitados.

    O valor medido é específico da topologia do Render e mora em
    `render.yaml`. No modelo genérico só cabe o padrão que falha fechado.

    Achado do Codex (P1), reproduzido de ponta a ponta antes de ser aceito: a
    primeira versão desta fatia escreveu `3` aqui.
    """
    assert ENV_EXEMPLO.exists(), 'env.example sumiu'
    valores = _valores_declarados(ENV_EXEMPLO.read_text(encoding='utf-8'))
    assert valores, (
        f'env.example deixou de documentar {VARIAVEL}; quem copia o modelo '
        'perde a variável de vista'
    )
    for valor in valores:
        assert valor == '0', (
            f'env.example declara {VARIAVEL}={valor}. Modelo genérico com valor '
            'topológico vira buraco em implantação sem proxy: o cliente '
            'completa a cadeia e escolhe o próprio balde'
        )


# ── R05-4: o contrato bate com a evidência medida ───────────────────────────

def test_r05_4_o_contrato_e_coerente_consigo_mesmo():
    campos = _campos_do_contrato()

    if not _determinado():
        assert campos['SALTOS-CONFIAVEIS'] == 'nao-determinado', \
            'a cadeia está INDETERMINADA mas o contrato já traz um número'
        assert campos['ORIGENS-CORROBORADAS'] == 'nao-determinado', \
            'a cadeia está INDETERMINADA mas o contrato já conta origens'
        return

    modelo = campos['MODELO-DA-BORDA']
    assert modelo in VEREDITOS_CONHECIDOS, f'modelo de borda desconhecido: {modelo}'
    assert modelo in MODELOS_QUE_FECHAM, (
        f'modelo {modelo} não fecha contrato: não dá para provar o número a '
        'partir dele'
    )

    evidencia = campos['EVIDENCIA']
    # `EVIDENCIA:` sozinho parseia para string vazia, que é != do marcador e
    # passava. O contrato podia fechar sem registrar nada.
    assert evidencia and evidencia != 'nao-produzida', \
        'contrato DETERMINADO sem evidência registrada'

    saltos = int(campos['SALTOS-CONFIAVEIS'])
    if modelo in ('PASSA_DIRETO', 'HIGIENIZA'):
        assert saltos == 0, (
            f'{modelo} significa que a borda não contribui nada confiável; '
            f'só 0 é compatível, o contrato diz {saltos}'
        )
    else:  # ANEXA é o único que sobra
        assert saltos >= 1, f'{modelo} significa que a borda contribui; 0 é incompatível'


def test_r05_4b_o_numero_do_contrato_e_o_numero_medido():
    """Amarra o contrato à tabela de medição do documento.

    Sem isto, `SALTOS-CONFIAVEIS` e a evidência são duas declarações
    independentes: trocar o número para 2 ou 4 passaria, com a tabela ao lado
    dizendo 3. Uma remedição legítima muda os dois juntos.
    """
    if not _determinado():
        return
    contribuicoes = _contribuicoes_medidas()
    assert len(contribuicoes) >= 3, (
        'a tabela de medição do documento perdeu linhas — a evidência dos três '
        f'controles é o que sustenta o número (encontrei {contribuicoes})'
    )
    assert len(set(contribuicoes)) == 1, (
        f'os controles registram contribuições diferentes: {contribuicoes}. '
        'Contribuição que varia com o que o cliente manda invalida o número'
    )
    saltos = int(_campos_do_contrato()['SALTOS-CONFIAVEIS'])
    assert saltos == contribuicoes[0], (
        f'o contrato diz {saltos} saltos e a medição registrada diz '
        f'{contribuicoes[0]} — um dos dois está errado'
    )


def test_r05_4c_o_documento_registra_o_que_a_medicao_nao_prova():
    """Uma origem mede um caminho. Enquanto `ORIGENS-CORROBORADAS` for menor
    que 2, o documento tem de dizer o que a amostra não cobre — amostragem
    refuta um roteamento divergente, não prova que toda rota tenha esta forma.

    Registrar o limite é o que separa um número medido de um número que parece
    medido."""
    if not _determinado():
        return
    origens = _campos_do_contrato()['ORIGENS-CORROBORADAS']
    assert origens.isdigit() and int(origens) >= 1, (
        f'contrato DETERMINADO com ORIGENS-CORROBORADAS={origens!r}'
    )
    if int(origens) >= 2:
        return
    texto = CONTRATO.read_text(encoding='utf-8')
    assert 'O que a medição NÃO estabelece' in texto, (
        'o contrato fechou com uma origem só e o documento não registra o que '
        'a medição não cobre'
    )
    assert 'Uma origem mede um caminho' in texto, \
        'sumiu do documento a ressalva sobre medir de uma origem só'


def test_r05_4d_o_documento_separa_o_medido_do_inferido():
    """A sonda devolvia FORMA, nunca identidade — era essa a propriedade de
    privacidade que a fazia aceitável. Então o número está sustentado por duas
    afirmações de naturezas diferentes:

    medido    a borda contribui com 3, e a contribuição não muda com o cliente;
    inferido  o primeiro desses 3 é o endereço de origem.

    A inferência tem contraexemplo que a medição não separa: um proxy
    compartilhado a montante, que repasse o cabeçalho intocado e não acrescente
    entrada própria, produz as três formas byte a byte iguais — e `cadeia[-3]`
    seria ele, igual para todos. A consequência é colapso, não spoofing, mas o
    documento não pode apresentar a inferência como observação.

    A primeira versão deste documento fazia exatamente isso. Achado do Codex
    (P1), confirmado por construção antes de ser aceito.
    """
    if not _determinado():
        return
    texto = CONTRATO.read_text(encoding='utf-8')

    # Pelo CABEÇALHO, não por substring solta: a primeira versão deste gate
    # procurava a frase no documento inteiro, e ela também aparece na remissão
    # do §3 — apagar a seção deixava o gate verde. A sabotagem mostrou.
    cabecalhos = [linha.strip() for linha in texto.splitlines()
                  if linha.startswith('#')]
    assert '### O que é medido e o que é inferido' in cabecalhos, (
        'sumiu do documento a seção que separa a forma medida da identidade '
        f'inferida de `cadeia[-N]`. Cabeçalhos presentes: {cabecalhos}'
    )

    # Dentro da SEÇÃO, não no documento inteiro. Duas sabotagens seguidas
    # passaram por causa disso: a frase procurada também aparece na remissão do
    # §3, então apagá-la do §2 deixava o gate verde.
    #
    # E com espaço normalizado: o documento é quebrado em ~78 colunas, então
    # uma frase procurada como substring literal atravessa quebra de linha e
    # não casa. A primeira versão reprovou sozinha por isso, e o motivo era o
    # gate, não o documento.
    corpo = texto.split('### O que é medido e o que é inferido', 1)[1]
    corpo = corpo.split('\n---', 1)[0].split('\n## ', 1)[0]
    corrido = ' '.join(corpo.split())

    for marca, falta in (
        ('**Medido:**', 'o que os controles realmente estabelecem'),
        ('**Inferido:**', 'a parte que não foi observada'),
        ('proxy compartilhado a montante', 'o contraexemplo'),
        ('colapso, não spoofing', 'a natureza da consequência'),
    ):
        assert marca in corrido, f'sumiu da seção {falta} ({marca!r})'


# ── R05-5: a sonda temporária saiu, e não volta ─────────────────────────────

def test_r05_5_a_sonda_nao_esta_no_repositorio():
    """Diagnóstico não vira API. Enquanto a cadeia estava INDETERMINADA a sonda
    podia existir; depois que ela cumpriu a função, ficar é dívida."""
    if not _determinado():
        assert SONDA_MODULO.exists(), \
            'a cadeia ainda está INDETERMINADA e a sonda já sumiu'
        return

    assert not SONDA_MODULO.exists(), (
        'cadeia DETERMINADA e a sonda continua no repositório — ela era '
        'temporária por contrato'
    )
    assert not SCRIPT_SONDA.exists(), (
        'o script de certificação continua no repositório; ele só fala com a '
        'rota que foi removida, então é código morto'
    )
    rotas = ROTAS_AUTH.read_text(encoding='utf-8')
    assert ROTA_DA_SONDA not in rotas, 'a rota da sonda continua registrada'
    assert 'proxy_chain_probe' not in rotas, \
        'o handler da sonda continua em modules/auth/routes.py'


def test_r05_5b_nenhum_arquivo_do_projeto_menciona_a_rota_da_sonda():
    """Não basta o handler sair: uma referência sobrevivente — um registro de
    rota esquecido, um cliente, um teste que ainda a chame — mantém o
    diagnóstico vivo por outro caminho."""
    if not _determinado():
        return
    sobreviventes = []
    for caminho in RAIZ.rglob('*'):
        if not caminho.is_file() or caminho.suffix not in ('.py', '.yaml', '.yml', '.js'):
            continue
        if '__pycache__' in caminho.parts or '.git' in caminho.parts:
            continue
        if caminho == Path(__file__):
            continue
        if ROTA_DA_SONDA in caminho.read_text(encoding='utf-8', errors='replace'):
            sobreviventes.append(str(caminho.relative_to(RAIZ)))
    assert not sobreviventes, f'a rota da sonda ainda aparece em: {sobreviventes}'


# ── R05-6: a chave da sonda não é dependência de nada ───────────────────────

def test_r05_6_a_chave_da_sonda_nao_e_dependencia_de_nenhum_caminho():
    """`PROXY_CHAIN_PROBE_KEY` existia só para a sonda. Com a sonda fora, nada
    pode continuar lendo essa variável: uma leitura sobrevivente significaria
    que algum caminho ainda depende de um segredo que o operador vai apagar do
    painel."""
    if not _determinado():
        return

    sobreviventes = []
    for caminho in RAIZ.rglob('*'):
        # Só CÓDIGO. A primeira versão desta condicional varreu `.md` também,
        # e reprovou pela instrução do §4 da R0.5 que manda o operador REMOVER
        # a variável — menção não é dependência, e o gate existe para proibir
        # dependência.
        if not caminho.is_file() or caminho.suffix not in ('.py', '.yaml', '.yml', '.js'):
            continue
        if '__pycache__' in caminho.parts or '.git' in caminho.parts:
            continue
        if caminho == Path(__file__):
            continue
        if CHAVE_DA_SONDA in caminho.read_text(encoding='utf-8', errors='replace'):
            sobreviventes.append(str(caminho.relative_to(RAIZ)).replace('\\', '/'))

    if _identidade_em_aberto():
        # A R0.5B reabriu a leitura da chave — mas só para as superfícies que
        # ela declara. Qualquer outra é regressão.
        fora = [c for c in sobreviventes if c not in SUPERFICIES_R05B]
        assert not fora, (
            f'{CHAVE_DA_SONDA} é lida fora das superfícies que a R0.5B declara: '
            f'{fora}. Autorizadas: {list(SUPERFICIES_R05B)}'
        )
        return

    assert not sobreviventes, (
        f'{CHAVE_DA_SONDA} ainda é lida em: {sobreviventes}. A variável some do '
        'painel do Render no fechamento da R0.5'
    )


# ── R05-7: a origem falha fechada quando a configuração é inválida ──────────

def _hops_com_ambiente(valor):
    """Import limpo em processo separado. `importlib.reload` aqui dentro criaria
    limitadores novos enquanto `modules/auth/routes.py` continuaria apontando
    para os antigos — efeito colateral silencioso sobre estado global."""
    ambiente = {k: v for k, v in os.environ.items() if k != VARIAVEL}
    if valor is not None:
        ambiente[VARIAVEL] = valor
    ambiente['PYTHONPATH'] = str(RAIZ)
    return subprocess.run(
        [sys.executable, '-c',
         f'import core.rate_limit as RL; print(RL.{"TRUSTED_PROXY_HOPS"})'],
        capture_output=True, text=True, env=ambiente, cwd=str(RAIZ),
        timeout=60, check=False)


def test_r05_7_sem_configuracao_o_padrao_continua_zero():
    """O gate que o `R05-8b` não cobre: ele força a confiança antes de exercitar
    o comportamento, então nunca enxerga o INICIALIZADOR. Trocar o default de
    `'0'` para um número positivo faria implantação não configurada confiar no
    cabeçalho do cliente — e passaria por toda a suíte."""
    saida = _hops_com_ambiente(None)
    assert saida.returncode == 0, f'import limpo falhou: {saida.stderr}'
    assert saida.stdout.strip() == '0', (
        f'sem {VARIAVEL} no ambiente o padrão virou {saida.stdout.strip()!r} — '
        'implantação não configurada passaria a confiar no cabeçalho do cliente'
    )


def test_r05_7b_configuracao_invalida_nao_vira_confianca():
    """Valor vazio ou negativo cai para 0; valor não numérico derruba a subida
    do processo. Nenhum dos dois pode virar confiança silenciosa."""
    for invalido in ('', '-5', '-1'):
        saida = _hops_com_ambiente(invalido)
        assert saida.returncode == 0, f'{invalido!r} quebrou o import: {saida.stderr}'
        assert saida.stdout.strip() == '0', (
            f'{VARIAVEL}={invalido!r} virou {saida.stdout.strip()!r} em vez de 0'
        )

    # Não numérico: o processo NÃO sobe. Falha barulhenta e reversível, em vez
    # de silenciosa — e nunca uma confiança que ninguém pediu.
    saida = _hops_com_ambiente('abc')
    assert saida.returncode != 0, (
        f'{VARIAVEL}=abc não derrubou o import; a aplicação subiria com uma '
        'configuração que ninguém consegue ler'
    )
    assert 'ValueError' in saida.stderr


def test_r05_7c_cadeia_mais_curta_que_a_declarada_cai_no_peer():
    """A requisição que não atravessou a cadeia esperada não prova origem
    nenhuma. Com o contrato em 3, uma cadeia de 2 elementos vale o peer."""
    saltos = int(_campos_do_contrato().get('SALTOS-CONFIAVEIS', 0) or 0)
    if saltos < 1:
        return
    anterior = RL.TRUSTED_PROXY_HOPS
    RL.TRUSTED_PROXY_HOPS = saltos
    try:
        curta = ', '.join(f'192.0.2.{i}' for i in range(10, 10 + saltos - 1))
        assert RL.get_client_ip(_HandlerFalso(peer='192.0.2.55', xff=curta)) == '192.0.2.55'
        assert RL.get_client_ip(_HandlerFalso(peer='192.0.2.55', xff='')) == '192.0.2.55'
    finally:
        RL.TRUSTED_PROXY_HOPS = anterior


# ── R05-8: a proteção anti-spoofing da R0 continua de pé ────────────────────

class _HandlerFalso:
    def __init__(self, peer='192.0.2.55', xff=None):
        self.client_address = (peer, 54321)
        self.headers = {} if xff is None else {'X-Forwarded-For': xff}


def test_r05_8_o_primeiro_elemento_do_xff_nunca_volta_a_ser_a_origem():
    fonte = inspect.getsource(RL.get_client_ip)
    assert 'cadeia[0]' not in fonte, \
        'get_client_ip voltou a ler o primeiro elemento da cadeia'
    assert "split(',')[0]" not in fonte, \
        "voltou o split(',')[0] que a R0 removeu"
    assert 'TRUSTED_PROXY_HOPS' in fonte, \
        'a origem deixou de consultar a confiança declarada'


def test_r05_8b_sem_salto_declarado_o_cabecalho_nao_muda_a_origem():
    """O comportamento, não só a forma do código."""
    anterior = RL.TRUSTED_PROXY_HOPS
    RL.TRUSTED_PROXY_HOPS = 0
    try:
        sem = RL.get_client_ip(_HandlerFalso(peer='192.0.2.7'))
        com = RL.get_client_ip(_HandlerFalso(peer='192.0.2.7',
                                             xff='192.0.2.10, 192.0.2.11'))
        assert sem == com == '192.0.2.7', \
            'o cabeçalho voltou a decidir origem sem proxy confiável declarado'
    finally:
        RL.TRUSTED_PROXY_HOPS = anterior


def test_r05_8c_com_a_cadeia_medida_o_cliente_nao_escolhe_o_proprio_bucket():
    """O gate que a medição tornou possível, e o que ela realmente prova.

    Com o contrato em 3 e a borda acrescentando 3, o que o cliente escreve fica
    à ESQUERDA da janela. Mandar mais lixo alonga a cadeia e empurra o lixo para
    longe de `cadeia[-3]` — nunca para dentro dela. É o controle C da medição,
    reencenado aqui com a cadeia que ele registrou.
    """
    saltos = int(_campos_do_contrato().get('SALTOS-CONFIAVEIS', 0) or 0)
    if saltos < 1:
        return
    anterior = RL.TRUSTED_PROXY_HOPS
    RL.TRUSTED_PROXY_HOPS = saltos
    try:
        # A borda acrescenta `saltos` elementos, e o PRIMEIRO deles é o
        # endereço do cliente: P1 acrescenta o cliente, P2 acrescenta P1, P3
        # acrescenta P2. São 3 no total, não cliente mais três — a primeira
        # versão deste gate montou quatro e ele reprovou, com razão.
        cliente = '192.0.2.99'
        # Gerada a partir de `saltos`, não escrita como lista fixa: com uma
        # lista fixa o gate reprovava por falta de elementos quando o contrato
        # declarava um número maior, em vez de reprovar pela propriedade.
        contribuicao = [cliente] + [f'192.0.2.{200 + i}' for i in range(saltos - 1)]
        assert len(contribuicao) == saltos
        buckets = set()
        for i in range(8):
            forjado = ', '.join(f'192.0.2.{j}' for j in range(10, 10 + i))
            cadeia = ([forjado] if forjado else []) + contribuicao
            buckets.add(RL.get_client_ip(
                _HandlerFalso(peer='10.0.0.1', xff=', '.join(cadeia))))
        assert buckets == {cliente}, (
            f'variar o cabeçalho produziu {len(buckets)} buckets: {sorted(buckets)}. '
            'O cliente voltou a escolher a própria identidade de limitação'
        )
    finally:
        RL.TRUSTED_PROXY_HOPS = anterior


def test_r05_8d_os_limites_numericos_nao_foram_tocados():
    """Esta fatia muda QUEM ocupa o bucket, não QUANTAS requisições ele aceita."""
    esperado = {
        'login_limiter': (10, 60),
        'recovery_limiter': (5, 300),
        'tenant_limiter': (60, 60),
        'supplier_portal_limiter': (30, 60),
    }
    for nome, (chamadas, periodo) in esperado.items():
        limitador = getattr(RL, nome)
        assert (limitador._max, limitador._period) == (chamadas, periodo), \
            f'{nome} mudou de limite: {limitador._max}/{limitador._period}s'


# ── R05-9: nenhum endereço real em lugar nenhum da fatia ────────────────────

FAIXAS_SEGURAS = (
    '192.0.2.0/24',     # TEST-NET-1
    '198.51.100.0/24',  # TEST-NET-2
    '203.0.113.0/24',   # TEST-NET-3
    '10.0.0.0/8',       # RFC 1918
    '172.16.0.0/12',
    '192.168.0.0/16',
    '100.64.0.0/10',    # RFC 6598 (CGNAT)
    '127.0.0.0/8',
    '0.0.0.0/8',
)


def test_r05_9_nenhum_endereco_real_na_fatia():
    """Nada nesta fatia — código, teste ou documento — pode carregar endereço
    de gente de verdade. Os sentinelas são espaço de documentação; o resto é
    faixa reservada."""
    import ipaddress

    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    padrao = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
    for caminho in (CONTRATO, Path(__file__)):
        texto = caminho.read_text(encoding='utf-8')
        for literal in set(padrao.findall(texto)):
            try:
                endereco = ipaddress.ip_address(literal)
            except ValueError:
                continue
            assert any(endereco in faixa for faixa in faixas), (
                f'{caminho.name} contém {literal}, que não é de faixa reservada'
            )
