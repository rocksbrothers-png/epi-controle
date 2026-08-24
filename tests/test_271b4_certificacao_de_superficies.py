"""Certificação final da frente #271 — B4-A.

## O que esta fatia acrescenta ao que já existia

`test_271_paridade_de_superficies.py` (B3) já afirma cada regra nas duas
IMPLEMENTAÇÕES: Dart e JavaScript. Isso responde "as duas bases de código
concordam?".

Não responde outra pergunta, que a auditoria de implantação tornou visível:
**as mesmas capacidades chegam a todos os ambientes onde o produto roda?**

São coisas diferentes. Os `render.yaml` dos dois repositórios mostram duas
arquiteturas de deploy:

- **Corporativo** (`epi-controle`) — um serviço Docker. `app.py` serve
  `static/` (Web Legado) e o Flutter Web vem EMBUTIDO em `./static/app/`,
  servido em `/app/` pelo mesmo Python. Mesmo origin, sem CORS.

- **SaaS** (`epi-controle-app`) — dois serviços. A API Docker serve `static/`
  e fala com um Supabase PRÓPRIO; o Flutter Web é um static site na RAIZ `/`,
  com `--base-href /` e `--dart-define=API_BASE_URL=` apontando para a API.
  Origins diferentes → CORS obrigatório.

Ou seja: **4 superfícies funcionais × 2 deployments = 8 combinações**, e
quatro coisas podem divergir com o código idêntico:

1. `CORS_ALLOW_ORIGIN` errado → o Flutter Web do SaaS perde TODAS as
   capacidades, com o Dart intacto;
2. `base-href` (`/app/` × `/`) → muda o routing do go_router, e portanto os
   deep links da B2-a;
3. `API_BASE_URL` compilado no build do SaaS × mesmo-origin no corporativo;
4. bancos separados → as migrations 025/026/027 precisam existir nos dois
   artefatos, senão a configuração por Unidade não tem onde gravar.

## O que este arquivo prova, e o que NÃO prova

Prova, em CI, sem acesso a ambiente: o inventário de superfícies, as
capacidades em cada base de código, a configuração de deploy DECLARADA e as
garantias transversais de comportamento (estas últimas executando o backend
de verdade, não lendo texto).

**Não prova** que o deployment está saudável: CORS efetivo, schema aplicado no
banco certo e disponibilidade só se verificam contra o ambiente publicado.
Isso é a B4-B (`scripts/certificar_deployment.py`), que exige URL e
credenciais e por isso roda em `workflow_dispatch`. Enquanto não for
executada, a frente fica **NOT CERTIFIED** para deployment — e ausência de
execução não é verde.
"""

import ast
import re
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

FLUTTER = RAIZ / 'flutter'
DART_CUBIT = FLUTTER / 'apps' / 'epi_admin' / 'lib' / 'core' / 'bloc' / 'stock_config_cubit.dart'
DART_TELA = FLUTTER / 'apps' / 'epi_admin' / 'lib' / 'features' / 'stock' / 'stock_config_screen.dart'
# A superfície Dart da configuração não é só o cubit e a tela: a AUTORIZAÇÃO
# mora na entrada (`stock_screen.dart`, que decide se o acesso aparece) e no
# gate de rota (`route_permissions.dart`). Uma definição que ignorasse esses
# dois afirmaria que o Dart não tem autorização — foi o que a primeira versão
# deste arquivo concluiu, erradamente.
DART_ENTRADA = FLUTTER / 'apps' / 'epi_admin' / 'lib' / 'features' / 'stock' / 'stock_screen.dart'
DART_ROTAS = FLUTTER / 'apps' / 'epi_admin' / 'lib' / 'core' / 'router' / 'route_permissions.dart'
JS_CONFIG = RAIZ / 'static' / 'js' / 'views' / 'estoque-config.js'
JS_HARNESS = RAIZ / 'static' / 'js' / 'test' / 'run-tests.js'
BACKEND_CI = RAIZ / '.github' / 'workflows' / 'backend-ci.yml'
CERTIFICACAO = RAIZ / '.github' / 'workflows' / 'certificacao-271.yml'
IOS_CI = RAIZ / '.github' / 'workflows' / 'ios_ci.yml'
SMOKE = RAIZ / 'scripts' / 'certificar_deployment.py'
RENDER = RAIZ / 'render.yaml'
DOCKERFILE = RAIZ / 'Dockerfile'


def _sem_comentarios_js(texto: str) -> str:
    sem_bloco = re.sub(r'/\*.*?\*/', '', texto, flags=re.DOTALL)
    return '\n'.join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith('//')
    )


def _sem_comentarios_dart(texto: str) -> str:
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('//') and not linha.lstrip().startswith('///')
    )


#: Os quatro arquivos que, juntos, SÃO a superfície Dart da configuração.
DART_SUPERFICIE = (DART_CUBIT, DART_TELA, DART_ENTRADA, DART_ROTAS)


def _dart() -> str:
    return _sem_comentarios_dart(
        '\n'.join(c.read_text(encoding='utf-8') for c in DART_SUPERFICIE)
    )


def _js() -> str:
    return _sem_comentarios_js(JS_CONFIG.read_text(encoding='utf-8'))


# ── 1. Inventário de superfícies × deployments ───────────────────────────────
#
# A matriz é DADO, não prosa. Uma superfície nova sem entrada aqui, ou uma
# entrada que deixe de ser verdade, reprova.

#: superfície funcional → base de código que a implementa
SUPERFICIES = {
    'Flutter Web': 'dart',
    'Android': 'dart',
    'iOS': 'dart',
    'Web Legado': 'js',
}

#: deployment → como cada superfície é publicada nele
DEPLOYMENTS = {
    'corporativo': {
        'repo': 'epi-controle',
        'Web Legado': 'servido por app.py na raiz do container',
        'Flutter Web': 'embutido em ./static/app/, servido em /app/ (mesmo origin)',
        'Android': 'com.rocksbrothers',
        'iOS': 'bundle corporativo',
    },
    'saas': {
        'repo': 'epi-controle-app',
        'Web Legado': 'servido pela API Docker',
        'Flutter Web': 'static site na raiz /, origin separado (CORS)',
        'Android': 'com.livamobile',
        'iOS': 'bundle Liva',
    },
}

#: As doze capacidades que a #271 entregou. Cada uma precisa existir em TODA
#: base de código — não há superfície com menos.
CAPACIDADES = (
    'selecionar Unidade autorizada',
    'mínimo por Unidade + EPI',
    'percentual de atenção',
    'habilitar/desabilitar alerta',
    'restaurar herança',
    'origem da configuração',
    'attention_limit',
    'stock_status',
    'fail-closed sem Unidade',
    'nenhuma opção Todas em escrita',
    'autorização vinda do backend',
    'isolamento entre Unidades',
)


def test_o_inventario_de_superficies_esta_completo():
    """Quatro superfícies, dois deployments, oito combinações.

    O gate não pode considerar a frente concluída com uma superfície fora da
    matriz — foi exatamente assim que o SaaS quase saiu do escopo, por não
    existir uma pasta com esse nome.
    """
    assert len(SUPERFICIES) == 4
    assert set(DEPLOYMENTS) == {'corporativo', 'saas'}
    for nome, config in DEPLOYMENTS.items():
        faltando = [s for s in SUPERFICIES if s not in config]
        assert not faltando, f'{nome} não declara como publica: {faltando}'


def test_cada_capacidade_existe_em_toda_base_de_codigo():
    """A matriz capacidade × base, provada por âncora real no fonte.

    Dart cobre Flutter Web, Android e iOS (mesmo código); JS cobre o Web
    Legado. Uma capacidade que suma de um lado reprova aqui antes de sumir de
    uma loja de aplicativos.
    """
    dart, js = _dart(), _js()
    ancoras = {
        'selecionar Unidade autorizada': ('EpiUnitSelector', 'readSelectableUnits'),
        'mínimo por Unidade + EPI': ('setUnitEpiMinimum', 'minimumPayload'),
        'percentual de atenção': ('setUnitEpiAttentionPercentage', 'attentionPayload'),
        'habilitar/desabilitar alerta': ('setUnitEpiAlertEnabled', 'alertPayload'),
        'restaurar herança': ('restoreUnitEpiMinimum', 'restorePayload'),
        'origem da configuração': ('isUnitConfigured', 'sourceLabel'),
        'attention_limit': ('attentionLimit', 'attentionLimit'),
        'stock_status': ('stockStatus', 'stockStatus'),
        'fail-closed sem Unidade': ('hasScope', 'canWrite'),
        'nenhuma opção Todas em escrita': ('UnitSelectorPurpose.write', 'allowsAllUnits'),
        'autorização vinda do backend': ('stock:adjust', 'stock:adjust'),
        'isolamento entre Unidades': ('_parCorrente', 'acceptUnit'),
    }
    assert set(ancoras) == set(CAPACIDADES), 'a lista de capacidades divergiu das âncoras'
    for capacidade, (ancora_dart, ancora_js) in ancoras.items():
        assert ancora_dart in dart, f'Dart perdeu: {capacidade}'
        assert ancora_js in js, f'Web Legado perdeu: {capacidade}'


# ── 2. Configuração de deploy declarada ──────────────────────────────────────

def _deployment_deste_repositorio() -> str:
    """Qual dos dois deployments este repositório publica.

    **Esta função é o coração da categoria B.** Os dois repos compartilham a
    base de código e publicam ARQUITETURAS DIFERENTES: um serviço com o Flutter
    embutido em `/app/` versus dois serviços com o Flutter na raiz e CORS.

    Um gate de paridade que exigisse a mesma configuração de deploy nos dois
    estaria errado — e a primeira versão deste arquivo estava: ela afirmava a
    arquitetura corporativa e reprovava no espelho, onde a diferença é
    intencional. O que precisa ser igual é a CAPACIDADE; o que é legitimamente
    diferente é como cada ambiente a publica.
    """
    render = RENDER.read_text(encoding='utf-8')
    return 'saas' if 'SaaS' in render or 'livamobile' in render else 'corporativo'


def test_o_repositorio_declara_a_arquitetura_do_seu_deployment():
    """Cada repo precisa publicar a superfície Flutter Web de ALGUM jeito
    coerente — e o jeito é diferente entre eles, de propósito."""
    deployment = _deployment_deste_repositorio()
    render = RENDER.read_text(encoding='utf-8')
    docker = DOCKERFILE.read_text(encoding='utf-8')
    assert 'type: web' in render

    if deployment == 'corporativo':
        # Um serviço: o Python serve `static/` e o Flutter vem EMBUTIDO em
        # `/app/`. O go_router resolve os deep links da B2-a a partir daí.
        assert './static/app/' in docker, \
            'o Flutter deixou de ser embutido em /app/ no corporativo'
        assert 'flutter-builder' in docker
    else:
        # Dois serviços, origins separados. O Flutter Web é publicado à parte,
        # com `base-href /` e a API endereçada por `--dart-define`.
        assert '--base-href /' in render, 'o SaaS precisa publicar na raiz'
        assert 'API_BASE_URL' in render, 'o SaaS precisa endereçar a API'
        assert 'CORS_ALLOW_ORIGIN' in render, \
            'origins separados exigem CORS — sem ele o Flutter Web perde tudo'


def test_os_dois_deployments_estao_declarados_no_inventario():
    """O repo em que este teste roda precisa constar da matriz."""
    assert _deployment_deste_repositorio() in DEPLOYMENTS


def test_as_migrations_da_configuracao_existem_no_artefato():
    """Bancos separados: a tabela precisa existir nos DOIS.

    Sem a migration no artefato, o deployment sobe e a configuração por
    Unidade não tem onde gravar — capacidade ausente com código idêntico.
    Aqui se prova a PRESENÇA; que ela foi APLICADA é a B4-B.
    """
    migracoes = RAIZ / 'epi_backend' / 'migrations'
    nomes = {p.name for p in migracoes.glob('*.py')}
    for prefixo in ('025_unit_epi_minimum_stock', '026_stock_classification_config'):
        assert any(n.startswith(prefixo) for n in nomes), f'migration ausente: {prefixo}'
    sql = RAIZ / 'supabase' / 'migrations'
    assert list(sql.glob('*unit_epi_minimum_stock.sql'))
    assert list(sql.glob('*stock_classification_config.sql'))


# ── 3. Os testes JS deixaram de ser decorativos ──────────────────────────────

def test_o_harness_js_carrega_o_modulo_da_configuracao():
    """Sem isto o módulo da B3 tinha só garantia estrutural.

    Estrutural prova que uma linha existe; não prova que ela se comporta.
    `canWrite` podia estar escrito e devolver `true` para uma Unidade fora da
    lista sem nenhum gate perceber.
    """
    harness = JS_HARNESS.read_text(encoding='utf-8')
    assert "'views/estoque-config.js'" in harness


def test_os_testes_js_rodam_no_ci():
    """Um teste que existe e nunca roda não é gate.

    `run-tests.js` tinha centenas de asserções e não era referenciado por
    nenhum workflow. Parecia proteção no diff e não participava de decisão
    nenhuma — a classe de verde falso que esta frente já encontrou antes.
    """
    ci = BACKEND_CI.read_text(encoding='utf-8')
    assert 'run-tests.js' in ci, 'o harness JS não é executado por nenhum job'
    assert 'frontend-tests' in ci
    # E o job precisa rodar quando `static/` muda.
    assert 'static/**' in ci


def test_o_harness_js_cobre_a_configuracao_de_verdade():
    """Não basta carregar: precisa exercitar."""
    harness = JS_HARNESS.read_text(encoding='utf-8')
    assert '__EPI_ESTOQUE_CONFIG__' in harness
    casos = re.findall(r"test\('config: ([^']+)'", harness)
    assert len(casos) >= 15, f'cobertura JS insuficiente da configuração: {len(casos)}'


# ── 4. Certificação das superfícies Dart ─────────────────────────────────────

def _yaml_sem_comentarios(texto: str) -> str:
    """Descarta linhas de comentário antes de procurar código no workflow.

    Não é preciosismo. Os dois testes abaixo procuravam `build ios` e
    `no-codesign` no texto cru do `certificacao-271.yml`. Quando o job iOS
    passou a DELEGAR para o `ios_ci.yml`, o comentário que explica a mudança
    passou a citar as duas expressões — e os testes continuariam verdes
    descrevendo um build que este arquivo não faz mais. Confundir a
    documentação com o código foi o defeito que este arquivo já corrigiu em
    `test_a_formula_do_motor_b_nao_foi_alterada_no_congelamento`; aqui ele
    reapareceria pelo mesmo caminho.
    """
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('#')
    )


def test_existe_job_de_certificacao_das_superficies():
    """`flutter.yml` só dispara com `paths: flutter/**`.

    Correto para o dia a dia, e insuficiente para certificar o ESTADO FINAL da
    frente: a B3 não tocou em Dart, então Flutter/iOS não rodaram nem no PR nem
    na main, e a última prova de build ficou dois merges atrás. A certificação
    não pode depender do path do diff.
    """
    assert CERTIFICACAO.exists(), 'falta o workflow de certificação da #271'
    wf = _yaml_sem_comentarios(CERTIFICACAO.read_text(encoding='utf-8')).lower()
    assert 'workflow_dispatch' in wf
    for prova in ('flutter analyze', 'flutter test', 'build web', 'build apk'):
        assert prova in wf, f'a certificação não cobre: {prova}'
    # iOS não aparece como build aqui de propósito — ver o teste de delegação.
    assert 'ios_ci.yml' in wf, 'a certificação não cobre a superfície iOS'


def test_a_certificacao_cobre_as_superficies_dart():
    wf = _yaml_sem_comentarios(CERTIFICACAO.read_text(encoding='utf-8')).lower()
    assert 'emulator' in wf or 'integration' in wf, 'falta a integração Android'
    ios = _yaml_sem_comentarios(IOS_CI.read_text(encoding='utf-8')).lower()
    assert 'no-codesign' in ios, 'a receita de iOS precisa de build sem assinatura'


# ── 4b. iOS: uma receita só, e ela mora no ios_ci.yml ────────────────────────
#
# O `Runner.xcodeproj` não é versionado (#238). Todo build iOS depende de uma
# sequência de preparação que só o `ios_ci.yml` conhece. A primeira versão da
# certificação escreveu uma SEGUNDA receita, incompleta, que falhava em dois
# segundos. Estes gates existem para que ela não volte.

def test_a_certificacao_nao_reimplementa_a_receita_de_ios():
    """O gate principal desta correção.

    Reimplementar aqui é o mesmo defeito que produziu dois motores de reposição
    (#945) e a comparação `saldo × mínimo` copiada para SQL: duas definições do
    mesmo comportamento, que divergem no primeiro ajuste feito só de um lado.
    """
    wf = _yaml_sem_comentarios(CERTIFICACAO.read_text(encoding='utf-8'))
    assert 'uses: ./.github/workflows/ios_ci.yml' in wf, (
        'a certificação precisa CHAMAR o ios_ci.yml, não construir o iOS por conta própria'
    )
    for passo in ('flutter build ios', 'flutter create', 'wire_xcode.rb',
                  'verify_bundle_id.rb', 'pin_ios_deployment_target.rb',
                  'pod install'):
        assert passo not in wf, (
            f'{passo!r} apareceu no certificacao-271.yml. A receita de iOS tem uma '
            'fonte única — o ios_ci.yml. Se ela precisa mudar, mude lá.'
        )


def test_o_ios_ci_e_reutilizavel_sem_perder_os_gatilhos_proprios():
    """Virar reutilizável é ACRESCENTAR uma entrada, não trocar de porta."""
    wf = _yaml_sem_comentarios(IOS_CI.read_text(encoding='utf-8'))
    assert 'workflow_call:' in wf, 'o ios_ci.yml precisa ser chamável'
    for gatilho in ('push:', 'pull_request:', 'workflow_dispatch:'):
        assert gatilho in wf, (
            f'o gatilho {gatilho!r} sumiu do ios_ci.yml — ele continua sendo o CI '
            'de iOS do dia a dia, não só uma sub-rotina da certificação'
        )


def test_a_receita_de_ios_prepara_o_projeto_antes_de_construir():
    """Ordem, não presença.

    `flutter build ios` antes do `flutter create` é exatamente a falha que esta
    correção resolve: o projeto ainda não existe no disco.
    """
    wf = _yaml_sem_comentarios(IOS_CI.read_text(encoding='utf-8'))
    criacao = wf.find('flutter create')
    assert criacao != -1, 'a preparação do projeto iOS sumiu do ios_ci.yml'
    construcao = wf.find('flutter build ios')
    assert construcao != -1, 'o ios_ci.yml não constrói mais o iOS'
    assert criacao < construcao, (
        'há um `flutter build ios` ANTES do `flutter create`. O Runner.xcodeproj '
        'não é versionado (#238): construir antes de gerar falha com '
        '"Expected ios/Runner.xcodeproj but this file is missing".'
    )


#: A identidade iOS é o único ponto em que os dois `ios_ci.yml` divergem — e
#: divergem de propósito. O `certificacao-271.yml`, por não conter receita
#: nenhuma, segue byte-a-byte igual nos dois repositórios.
ORG_IOS = {
    'corporativo': 'com.rocksbrothers',
    'saas': 'com.livamobile',
}


def test_o_bundle_id_de_ios_pertence_a_este_repositorio():
    wf = IOS_CI.read_text(encoding='utf-8')
    esperado = ORG_IOS[_deployment_deste_repositorio()]
    assert f'--org {esperado}' in wf, (
        f'este repositório é {_deployment_deste_repositorio()} e deveria gerar o '
        f'projeto iOS com --org {esperado}'
    )
    outro = ORG_IOS['saas' if esperado == ORG_IOS['corporativo'] else 'corporativo']
    assert f'--org {outro}' not in wf, (
        f'o --org do outro deployment ({outro}) vazou para este repositório'
    )


def test_a_certificacao_nao_afrouxa_a_reprovacao():
    """Uma superfície reprovada tem de reprovar a certificação."""
    wf = _yaml_sem_comentarios(CERTIFICACAO.read_text(encoding='utf-8'))
    assert 'continue-on-error' not in wf, (
        'continue-on-error transforma reprovação em verde — é o oposto de certificar'
    )
    assert 'secrets: inherit' not in wf, (
        'o build iOS --no-codesign não precisa de secret nenhum; `inherit` entregaria '
        'todos os secrets do repositório ao workflow chamado sem necessidade'
    )
    assert 'superficie-ios' in wf.split('smoke-deployment')[1], (
        'o smoke de deployment (B4-B) precisa depender também da superfície iOS'
    )


# ── 5. B4-B: infraestrutura de smoke, sem fingir que foi executada ───────────

def test_o_smoke_de_deployment_existe_e_nao_carrega_credencial():
    """URLs e tokens entram por ambiente, nunca pelo repositório."""
    assert SMOKE.exists(), 'falta o script de certificação de deployment (B4-B)'
    fonte = SMOKE.read_text(encoding='utf-8')
    assert 'os.environ' in fonte or 'getenv' in fonte
    # Nenhum segredo literal.
    suspeitos = re.findall(r'(?i)(token|secret|password)\s*=\s*[\'"][^\'"]{8,}', fonte)
    assert not suspeitos, f'credencial embutida no script: {suspeitos}'


def test_o_smoke_cobre_os_dois_deployments():
    fonte = SMOKE.read_text(encoding='utf-8')
    assert 'corporativo' in fonte and 'saas' in fonte
    for verificacao in ('/api/units/selectable', '/api/stock/epis', 'cors'):
        assert verificacao in fonte.lower(), f'smoke não cobre: {verificacao}'


def test_o_smoke_nao_escreve_em_producao():
    """Certificar não pode alterar configuração real.

    Provar que a escrita funciona exige ambiente controlado; contra produção,
    só leitura e health. Um smoke que grava para se provar é um smoke que
    muda o alerta de alguém.
    """
    fonte = SMOKE.read_text(encoding='utf-8')
    arvore = ast.parse(fonte)
    metodos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            for kw in no.keywords:
                if kw.arg == 'method' and isinstance(kw.value, ast.Constant):
                    metodos.add(str(kw.value.value).upper())
    proibidos = metodos & {'POST', 'PUT', 'PATCH', 'DELETE'}
    assert not proibidos, f'o smoke escreve em produção: {proibidos}'


def test_o_estado_de_certificacao_e_explicito():
    """Ausência de execução não é verde.

    Enquanto a B4-B não rodar nos dois ambientes, a frente fica NOT CERTIFIED
    para deployment — e isso precisa estar escrito, não subentendido.
    """
    fonte = SMOKE.read_text(encoding='utf-8')
    assert 'NOT CERTIFIED' in fonte


# ── 6. Garantias transversais — COMPORTAMENTO, não texto ─────────────────────
#
# Os testes acima leem fontes. Estes executam o backend: são a régua contra a
# qual as duas UIs foram escritas, e provam a semântica que elas apenas
# exibem.

def _banco():
    """Empresa 1, Unidades 10/11/12, EPI 99 com mínimo corporativo 100."""
    from core.schema import ensure_stock_classification_config, ensure_unit_epi_minimum_stock
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, minimum_stock INTEGER);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER
        );
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'A'), (11, 1, 'B'), (12, 1, 'C');
        INSERT INTO epis (id, company_id, minimum_stock) VALUES (99, 1, 100);
        '''
    )
    ensure_unit_epi_minimum_stock(conn)
    ensure_stock_classification_config(conn)
    conn.commit()
    return conn


ATOR = {'id': 5, 'role': 'user', 'company_id': 1, 'full_name': 'Gestor'}


def test_alterar_a_unidade_A_nao_modifica_B_nem_C():
    """Isolamento, provado por execução.

    O defeito original da #271 era `UPDATE epis SET minimum_stock`: o Gestor da
    Unidade A reescrevia, em silêncio, o parâmetro de B e C.
    """
    from modules.stock.service import resolve_unit_minimum_stock, set_unit_epi_minimum_stock
    conn = _banco()
    set_unit_epi_minimum_stock(conn, 1, 10, 99, 7, actor=ATOR)
    conn.commit()
    assert resolve_unit_minimum_stock(conn, 1, 10, 99).value == 7
    for outra in (11, 12):
        herdado = resolve_unit_minimum_stock(conn, 1, outra, 99)
        assert herdado.value == 100, f'Unidade {outra} foi contaminada'
        assert herdado.source == 'company_default'


def test_mudar_o_padrao_corporativo_so_afeta_quem_herda():
    """Propagação é LEITURA, nunca UPDATE em massa.

    Quem decidiu um valor próprio fica intacto; quem herda passa a ver o novo
    na leitura seguinte.
    """
    from modules.stock.service import resolve_unit_minimum_stock, set_unit_epi_minimum_stock
    conn = _banco()
    set_unit_epi_minimum_stock(conn, 1, 10, 99, 7, actor=ATOR)   # A decide 7
    conn.execute('UPDATE epis SET minimum_stock = 50 WHERE id = 99')  # empresa muda
    conn.commit()
    assert resolve_unit_minimum_stock(conn, 1, 10, 99).value == 7, 'unit_configured foi sobrescrito'
    assert resolve_unit_minimum_stock(conn, 1, 11, 99).value == 50, 'quem herda não acompanhou'


def test_salvar_o_valor_do_padrao_nao_e_o_mesmo_que_restaurar():
    """Mesmo número, origens opostas — a distinção que a frente inteira
    existe para preservar."""
    from modules.stock.service import (
        clear_unit_epi_minimum_stock,
        resolve_unit_minimum_stock,
        set_unit_epi_minimum_stock,
    )
    conn = _banco()
    salvo = set_unit_epi_minimum_stock(conn, 1, 10, 99, 100, actor=ATOR)
    conn.commit()
    assert salvo.value == 100 and salvo.source == 'unit_configured'

    restaurado = clear_unit_epi_minimum_stock(conn, 1, 10, 99, actor=ATOR)
    conn.commit()
    assert restaurado.value == 100, 'o valor efetivo é o mesmo'
    assert restaurado.source == 'company_default', 'mas a origem é a oposta'
    assert resolve_unit_minimum_stock(conn, 1, 10, 99).source == 'company_default'


def test_alerta_desabilitado_nunca_vira_normal():
    """`disabled` é estado operacional; a condição física continua sendo dita
    por `underlying_status`. Um EPI silenciado não pode aparecer como saudável."""
    from modules.stock.service import classify_unit_epi_stock, set_unit_epi_alert_enabled
    conn = _banco()
    set_unit_epi_alert_enabled(conn, 1, 10, 99, False, actor=ATOR)
    conn.commit()
    # Saldo 1 contra mínimo 100 — crítico de fato.
    c = classify_unit_epi_stock(conn, 1, 10, 99, unit_stock=1)
    assert c.stock_status == 'disabled'
    assert c.stock_status != 'normal'
    assert c.underlying_status == 'critical', 'a verdade física foi perdida'


def test_as_tres_origens_tem_semantica_distinta():
    """`system_default` é do alerta; `company_default` é do mínimo e do
    percentual. Hierarquias de altura diferente."""
    from modules.stock.service import (
        ALERT_SOURCE_SYSTEM,
        ALERT_SOURCE_UNIT,
        ATTENTION_SOURCE_COMPANY,
        MINIMUM_SOURCE_COMPANY,
        MINIMUM_SOURCE_UNIT,
    )
    assert MINIMUM_SOURCE_UNIT == ALERT_SOURCE_UNIT == 'unit_configured'
    assert MINIMUM_SOURCE_COMPANY == ATTENTION_SOURCE_COMPANY == 'company_default'
    assert ALERT_SOURCE_SYSTEM == 'system_default'
    assert ALERT_SOURCE_SYSTEM != MINIMUM_SOURCE_COMPANY


def test_nenhum_cliente_recalcula_saldo_por_minimo():
    """O gate da 1.1D-C4 aplicado às duas bases, como certificação final."""
    from tests.stock_rule_scan import comparacoes_saldo_por_minimo, sem_comentarios
    for caminho in (DART_CUBIT, DART_TELA, JS_CONFIG):
        achados = comparacoes_saldo_por_minimo(
            sem_comentarios(caminho.read_text(encoding='utf-8'))
        )
        assert not achados, f'{caminho.name} recalcula: {achados}'


def test_nenhum_cliente_reconstroi_permissao_por_papel():
    """Lista de papéis no cliente é o antipadrão que a frente removeu."""
    for fonte in (_dart(), _js()):
        assert not re.search(r"\[\s*['\"]admin['\"]\s*,\s*['\"]user['\"]\s*\]", fonte), \
            'voltou a decidir autorização por lista de papéis'
        assert 'stock:adjust' in fonte, 'a permissão real sumiu'
