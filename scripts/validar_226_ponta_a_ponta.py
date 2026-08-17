#!/usr/bin/env python3
"""Validação ponta a ponta da issue #226 — vínculo local por Unidade.

Executa os sete cenários de ``docs/ROTEIRO_VALIDACAO_226.md`` contra a API
REAL: sobe ``app.py`` de verdade, que fala com PostgreSQL de verdade. Não há
mock, stub nem chamada direta a handler — cada asserção olha o corpo de uma
resposta HTTP ou o estado das tabelas depois dela.

Isso é deliberado. A suíte de testes já prova que cada camada honra o contrato
que lhe foi escrito; o que ela não prova é que as camadas, juntas e contra um
banco real, produzem o comportamento que o produto pediu. Um teste que chama o
handler direto pula o roteamento, a serialização e a resolução de ator — que é
justamente onde um escopo por Unidade costuma escapar.

Uso:
    DATABASE_URL=postgresql://... python3 scripts/validar_226_ponta_a_ponta.py

O banco é reconstruído a cada execução (as tabelas envolvidas são truncadas e
resemeadas), então rodar duas vezes dá o mesmo resultado.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = int(os.environ.get('EPI_E2E_PORT', '8731'))
BASE = f'http://127.0.0.1:{PORT}'

# ── ids fixos: o relatório fica legível e a falha, localizável ──────────────
CO_ALFA, CO_BETA = 1, 2
UNIT_NORTE, UNIT_SUL, UNIT_BETA = 1, 2, 3
EMP_ANCHOR_NORTE, EMP_ANCHOR_SUL, EMP_ANCHOR_BETA = 101, 102, 103
EMP_BELTRANO = 201
USER_NORTE, USER_SUL, USER_BETA, USER_GERAL = 11, 12, 13, 14
OSC_OMEGA = 301
CONTRACT_NORTE = 401


# ── infraestrutura mínima ──────────────────────────────────────────────────

class Resultado:
    def __init__(self):
        self.linhas = []
        self.falhas = 0

    def checar(self, cenario, descricao, condicao, detalhe=''):
        ok = bool(condicao)
        if not ok:
            self.falhas += 1
        self.linhas.append((cenario, descricao, ok, detalhe))
        return ok

    def imprimir(self):
        atual = None
        for cenario, descricao, ok, detalhe in self.linhas:
            if cenario != atual:
                print(f'\n{cenario}')
                atual = cenario
            marca = 'OK  ' if ok else 'FALHA'
            print(f'  [{marca}] {descricao}')
            if detalhe and not ok:
                print(f'          {detalhe}')
        total = len(self.linhas)
        print(f'\n{total - self.falhas}/{total} asserções passaram.')
        return self.falhas == 0


def http(metodo, caminho, *, corpo=None, espera=None):
    """Requisição HTTP crua. Devolve (status, json). Nunca levanta em 4xx —
    recusa é resultado esperado em vários cenários."""
    # O caminho carrega acentos ("Ômega"): sem quote, http.client tenta
    # encodar a request line em ASCII e estoura antes de sair da máquina.
    partes = caminho.split('?', 1)
    url = BASE + urllib.parse.quote(partes[0])
    if len(partes) == 2:
        url += '?' + urllib.parse.quote(partes[1], safe='=&')
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    if dados:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            texto = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as exc:
        texto = exc.read().decode()
        status = exc.code
    try:
        payload = json.loads(texto) if texto else {}
    except json.JSONDecodeError:
        payload = {'_raw': texto[:400]}
    if espera is not None and status != espera:
        print(f'  ! {metodo} {caminho} -> {status} (esperado {espera}): {payload}')
    return status, payload


def sql(connection, query, params=()):
    return connection.execute(query, params).fetchall()


def um(connection, query, params=()):
    linhas = sql(connection, query, params)
    return linhas[0][0] if linhas else None


# ── seed ───────────────────────────────────────────────────────────────────

def semear():
    """Dois tenants, três Unidades, uma empresa terceirizada e um colaborador
    terceirizado — cada um cadastrado UMA vez, como manda o domínio."""
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()

    with closing(get_connection()) as cx:
        for tabela in (
            'outsourced_company_unit_links', 'employee_unit_links', 'service_contracts',
            'outsourced_companies', 'employee_unit_movements', 'employees',
            'company_audit_logs', 'users', 'units', 'companies',
        ):
            cx.execute(f'TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE')

        for cid, nome, cnpj in ((CO_ALFA, 'Alfa Engenharia', '11.111.111/0001-11'),
                                (CO_BETA, 'Beta Serviços', '22.222.222/0001-22')):
            cx.execute(
                'INSERT INTO companies (id, name, legal_name, cnpj, logo_type) VALUES (?,?,?,?,?)',
                (cid, nome, nome, cnpj, ''),
            )

        for uid, cid, nome in ((UNIT_NORTE, CO_ALFA, 'Unidade Norte'),
                               (UNIT_SUL, CO_ALFA, 'Unidade Sul'),
                               (UNIT_BETA, CO_BETA, 'Unidade Beta')):
            cx.execute(
                'INSERT INTO units (id, company_id, name, unit_type, city) VALUES (?,?,?,?,?)',
                (uid, cid, nome, 'obra', 'São Paulo'),
            )

        # Colaboradores-âncora: é o `linked_employee_id` que dá Unidade
        # operacional ao Administrador Local (core.repository).
        ancoras = (
            (EMP_ANCHOR_NORTE, CO_ALFA, UNIT_NORTE, 'Ana Norte', 'CLT'),
            (EMP_ANCHOR_SUL, CO_ALFA, UNIT_SUL, 'Sara Sul', 'CLT'),
            (EMP_ANCHOR_BETA, CO_BETA, UNIT_BETA, 'Bruno Beta', 'CLT'),
            (EMP_BELTRANO, CO_ALFA, UNIT_NORTE, 'Beltrano de Souza', 'Terceirizado'),
        )
        for eid, cid, uid, nome, vinculo in ancoras:
            cx.execute(
                '''INSERT INTO employees
                   (id, company_id, unit_id, employee_id_code, name, sector, role_name,
                    admission_date, schedule_type, tipo_vinculo, outsourced_company_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (eid, cid, uid, f'MAT{eid}', nome, 'Operação', 'Operador',
                 '2026-01-05', 'administrativo', vinculo,
                 OSC_OMEGA if vinculo == 'Terceirizado' else None),
            )

        usuarios = (
            (USER_NORTE, CO_ALFA, 'admin_norte', 'admin', EMP_ANCHOR_NORTE),
            (USER_SUL, CO_ALFA, 'admin_sul', 'admin', EMP_ANCHOR_SUL),
            (USER_BETA, CO_BETA, 'admin_beta', 'admin', EMP_ANCHOR_BETA),
            (USER_GERAL, CO_ALFA, 'geral_alfa', 'general_admin', None),
        )
        for uid, cid, username, role, anchor in usuarios:
            cx.execute(
                '''INSERT INTO users (id, company_id, username, password, full_name, role, active, linked_employee_id)
                   VALUES (?,?,?,?,?,?,?,?)''',
                (uid, cid, username, 'x', username, role, 1, anchor),
            )

        # A Construtora Ômega é ÚNICA no tenant Alfa, originada na Norte.
        cx.execute(
            '''INSERT INTO outsourced_companies
               (id, company_id, unit_id, legal_name, trade_name, cnpj, cnpj_normalized,
                registration_mode, registration_status)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (OSC_OMEGA, CO_ALFA, UNIT_NORTE, 'Construtora Ômega LTDA', 'Ômega',
             '33.333.333/0001-33', '33333333000133', 'standard', 'complete'),
        )
        cx.execute(
            '''INSERT INTO service_contracts
               (id, company_id, outsourced_company_id, unit_id, contract_ref, start_date, end_date, status)
               VALUES (?,?,?,?,?,?,?,?)''',
            (CONTRACT_NORTE, CO_ALFA, OSC_OMEGA, UNIT_NORTE, 'CT-NORTE-001',
             '2026-01-01', '2026-12-31', 'active'),
        )
        # Estado inicial: só a Norte tem vínculo — com a empresa e com o
        # colaborador. A Sul começa sem enxergar nenhum dos dois.
        cx.execute(
            '''INSERT INTO outsourced_company_unit_links
               (company_id, outsourced_company_id, unit_id, local_status) VALUES (?,?,?,?)''',
            (CO_ALFA, OSC_OMEGA, UNIT_NORTE, 'active'),
        )
        cx.execute(
            '''INSERT INTO employee_unit_links
               (company_id, employee_id, unit_id, local_status) VALUES (?,?,?,?)''',
            (CO_ALFA, EMP_BELTRANO, UNIT_NORTE, 'active'),
        )

        # O módulo "terceirizados" nasce OCULTO (opt-in). Ligá-lo é passo real
        # do fluxo: sem isso o backend recusa o vínculo, e é o que se quer.
        from modules.settings.service import save_module_visibility
        for cid in (CO_ALFA, CO_BETA):
            for role in ('admin', 'general_admin'):
                save_module_visibility(
                    cx, cid, role,
                    {'terceirizados': True, 'terceirizados_colaboradores': True},
                )
        cx.commit()


def subir_servidor():
    env = dict(os.environ, EPI_PORT=str(PORT))
    proc = subprocess.Popen(
        [sys.executable, 'app.py'], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    for _ in range(60):
        if proc.poll() is not None:
            print('Servidor morreu ao subir:\n', proc.stdout.read()[-2000:])
            sys.exit(1)
        try:
            # `/health` responde vivo assim que o socket abre; o que interessa
            # é PRONTO. O bootstrap de schema roda em background e as rotas de
            # escrita devolvem 503 até ele concluir — esperar o errado faz o
            # cenário falhar por corrida, não por regra.
            with urllib.request.urlopen(f'{BASE}/health/ready', timeout=3) as resp:
                if resp.status == 200:
                    return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    print('Servidor não respondeu a tempo.')
    sys.exit(1)


# ── cenários ───────────────────────────────────────────────────────────────

def achar(itens, entity_id):
    for item in itens:
        if int(item.get('id', 0)) == entity_id:
            return item
    return None


def c1_empresa_multi_unidade(r):
    from core.database import get_connection
    cenario = 'C1 · Vínculo multi-Unidade de empresa, sem duplicar cadastro'

    _, busca = http('GET', f'/api/outsourced-companies/search?actor_user_id={USER_SUL}&q=Ômega')
    achado = achar(busca.get('outsourced_companies', []), OSC_OMEGA)
    r.checar(cenario, 'a Unidade Sul ENCONTRA a empresa que ainda não vinculou', achado is not None,
             f'busca devolveu {busca}')
    if achado:
        r.checar(cenario, 'o item vem MASCARADO (linked_units_count presente)',
                 achado.get('linked_units_count') is not None, f'item={achado}')
        r.checar(cenario, 'o item mascarado NÃO expõe local_status de outra Unidade',
                 achado.get('local_status') is None, f"local_status={achado.get('local_status')}")

    status, _ = http('POST', f'/api/outsourced-companies/{OSC_OMEGA}/link',
                     corpo={'actor_user_id': USER_SUL}, espera=201)
    r.checar(cenario, 'a Unidade Sul consegue criar o SEU vínculo local', status == 201, f'status={status}')

    _, lista = http('GET', f'/api/outsourced-companies?actor_user_id={USER_SUL}')
    vinculada = achar(lista.get('outsourced_companies', []), OSC_OMEGA)
    r.checar(cenario, 'a empresa passa a aparecer na listagem da Sul como ativa',
             vinculada is not None and vinculada.get('local_status') == 'active', f'item={vinculada}')

    with closing(get_connection()) as cx:
        cadastros = um(cx, 'SELECT COUNT(*) FROM outsourced_companies WHERE company_id = ?', (CO_ALFA,))
        vinculos = um(cx, 'SELECT COUNT(*) FROM outsourced_company_unit_links WHERE outsourced_company_id = ?',
                      (OSC_OMEGA,))
    r.checar(cenario, 'o cadastro corporativo NÃO foi duplicado (1 empresa)', cadastros == 1,
             f'outsourced_companies={cadastros}')
    r.checar(cenario, 'existem 2 vínculos, um por Unidade', vinculos == 2,
             f'outsourced_company_unit_links={vinculos}')


def c2_colaborador_multi_unidade(r):
    from core.database import get_connection
    cenario = 'C2 · Vínculo multi-Unidade de colaborador, sem duplicar cadastro'

    _, antes = http('GET', f'/api/employees?actor_user_id={USER_SUL}')
    r.checar(cenario, 'antes do vínculo, a Sul não vê o colaborador como vinculado',
             (achar(antes.get('employees', []), EMP_BELTRANO) or {}).get('is_linked_to_actor_unit') in (False, None, 0),
             f'item={achar(antes.get("employees", []), EMP_BELTRANO)}')

    status, _ = http('POST', f'/api/employees/{EMP_BELTRANO}/link',
                     corpo={'actor_user_id': USER_SUL}, espera=201)
    r.checar(cenario, 'a Unidade Sul consegue vincular o colaborador', status in (200, 201), f'status={status}')

    _, depois = http('GET', f'/api/employees?actor_user_id={USER_SUL}')
    item = achar(depois.get('employees', []), EMP_BELTRANO)
    r.checar(cenario, 'o colaborador aparece para a Sul com vínculo ativo',
             item is not None and item.get('local_unit_link_status') == 'active', f'item={item}')

    with closing(get_connection()) as cx:
        cadastros = um(cx, 'SELECT COUNT(*) FROM employees WHERE id = ?', (EMP_BELTRANO,))
        unidade = um(cx, 'SELECT unit_id FROM employees WHERE id = ?', (EMP_BELTRANO,))
        vinculos = um(cx, 'SELECT COUNT(*) FROM employee_unit_links WHERE employee_id = ?', (EMP_BELTRANO,))
    r.checar(cenario, 'o colaborador NÃO foi duplicado (1 linha)', cadastros == 1, f'employees={cadastros}')
    r.checar(cenario, 'employees.unit_id continua na Norte — vincular não é transferir',
             int(unidade) == UNIT_NORTE, f'unit_id={unidade}')
    r.checar(cenario, 'existem 2 vínculos, um por Unidade', vinculos == 2, f'employee_unit_links={vinculos}')


def c3_sem_heranca(r):
    from core.database import get_connection
    cenario = 'C3 · Ausência de herança entre Unidades'

    _, contratos = http('GET', f'/api/outsourced-companies/{OSC_OMEGA}/service-contracts?actor_user_id={USER_SUL}')
    refs = [c.get('contract_ref') for c in (contratos.get('service_contracts') or contratos.get('items') or [])]
    r.checar(cenario, 'a Sul NÃO herda o contrato de serviço da Norte',
             'CT-NORTE-001' not in refs, f'contratos visíveis para a Sul={refs}')

    with closing(get_connection()) as cx:
        linha = sql(cx, '''SELECT contract_number, cost_center_ref, local_responsible_id
                           FROM outsourced_company_unit_links
                           WHERE outsourced_company_id = ? AND unit_id = ?''',
                    (OSC_OMEGA, UNIT_SUL))
    novo = dict(zip(('contract_number', 'cost_center_ref', 'local_responsible_id'), linha[0])) if linha else {}
    r.checar(cenario, 'o vínculo da Sul nasce limpo (sem contrato/centro de custo/responsável herdados)',
             not (novo.get('contract_number') or '') and not (novo.get('cost_center_ref') or '')
             and novo.get('local_responsible_id') is None, f'vínculo da Sul={novo}')


def c4_arquivamento_local_independente(r):
    from core.database import get_connection
    cenario = 'C4 · Arquivamento local independente'

    status, corpo = http('POST', f'/api/outsourced-companies/{OSC_OMEGA}/unit-link/deactivate',
                         corpo={'actor_user_id': USER_SUL, 'reason': 'Obra da Sul encerrada'}, espera=200)
    r.checar(cenario, 'a Sul arquiva o SEU vínculo', status == 200 and corpo.get('local_status') == 'inactive',
             f'status={status} corpo={corpo}')

    with closing(get_connection()) as cx:
        sul = sql(cx, '''SELECT local_status, deactivation_reason, deactivated_by_user_id, deactivated_at
                         FROM outsourced_company_unit_links WHERE outsourced_company_id=? AND unit_id=?''',
                  (OSC_OMEGA, UNIT_SUL))[0]
        norte = um(cx, '''SELECT local_status FROM outsourced_company_unit_links
                          WHERE outsourced_company_id=? AND unit_id=?''', (OSC_OMEGA, UNIT_NORTE))
        corporativo = um(cx, 'SELECT status FROM outsourced_companies WHERE id = ?', (OSC_OMEGA,))
        total = um(cx, 'SELECT COUNT(*) FROM outsourced_company_unit_links WHERE outsourced_company_id = ?',
                   (OSC_OMEGA,))
    r.checar(cenario, 'o vínculo da Sul guarda motivo, ator e carimbo de tempo',
             sul[1] == 'Obra da Sul encerrada' and sul[2] == USER_SUL and bool(sul[3]), f'vínculo Sul={sul}')
    r.checar(cenario, 'o vínculo da NORTE permanece ativo e intocado', norte == 'active', f'norte={norte}')
    r.checar(cenario, 'o cadastro corporativo continua ativo', corporativo == 'active', f'status={corporativo}')
    r.checar(cenario, 'NENHUMA linha foi apagada — arquivar não é excluir', total == 2, f'vínculos={total}')


def c5_reativacao_com_historico(r):
    from core.database import get_connection
    cenario = 'C5 · Reativação preservando histórico'

    with closing(get_connection()) as cx:
        antes = sql(cx, '''SELECT id, deactivation_reason FROM outsourced_company_unit_links
                           WHERE outsourced_company_id=? AND unit_id=?''', (OSC_OMEGA, UNIT_SUL))[0]

    status, corpo = http('POST', f'/api/outsourced-companies/{OSC_OMEGA}/unit-link/activate',
                         corpo={'actor_user_id': USER_SUL}, espera=200)
    r.checar(cenario, 'a Sul reativa o vínculo arquivado',
             status == 200 and corpo.get('local_status') == 'active', f'status={status} corpo={corpo}')

    with closing(get_connection()) as cx:
        depois = sql(cx, '''SELECT id, local_status, deactivation_reason FROM outsourced_company_unit_links
                            WHERE outsourced_company_id=? AND unit_id=?''', (OSC_OMEGA, UNIT_SUL))[0]
        total = um(cx, 'SELECT COUNT(*) FROM outsourced_company_unit_links WHERE outsourced_company_id = ?',
                   (OSC_OMEGA,))
    r.checar(cenario, 'é a MESMA linha — o vínculo foi reaproveitado, não recriado',
             depois[0] == antes[0] and total == 2, f'id antes={antes[0]} depois={depois[0]} total={total}')
    r.checar(cenario, 'o vínculo voltou a ativo', depois[1] == 'active', f'local_status={depois[1]}')
    # As colunas `deactivated_*` do vínculo são ESTADO CORRENTE, e a reativação
    # as limpa de propósito: um vínculo ativo carregando "arquivado porque…"
    # leria como se ainda estivesse arquivado. O histórico vive na auditoria —
    # é lá que ele tem que sobreviver à reativação.
    r.checar(cenario, 'o vínculo ativo não carrega motivo de arquivamento obsoleto',
             not (depois[2] or ''), f'motivo residual={depois[2]!r}')
    with closing(get_connection()) as cx:
        trilha = sql(cx, '''SELECT details_json FROM company_audit_logs
                            WHERE company_id = ? AND action_type = ?
                            ORDER BY id''',
                     (CO_ALFA, 'outsourced_company_unit_link_status_changed'))
    registros = [json.loads(linha[0]) for linha in trilha]
    arquivamento = [
        reg for reg in registros
        if any(c['field'] == 'local_status' and c['after'] == 'inactive' for c in reg)
    ]
    r.checar(cenario, 'a auditoria preserva o arquivamento anterior', len(arquivamento) == 1,
             f'registros={registros}')
    if arquivamento:
        campos = {c['field']: c['after'] for c in arquivamento[0]}
        r.checar(cenario, 'e preserva o motivo, a Unidade e o papel de quem arquivou',
                 campos.get('reason') == 'Obra da Sul encerrada'
                 and campos.get('unit_id') == str(UNIT_SUL) and campos.get('actor_role') == 'admin',
                 f'campos={campos}')


def c6_null_nao_informado(r):
    cenario = 'C6 · null é "não informado", nunca "sem vínculo"'

    _, busca = http('GET', f'/api/outsourced-companies/search?actor_user_id={USER_GERAL}&q=Ômega')
    item = achar(busca.get('outsourced_companies', []), OSC_OMEGA)
    r.checar(cenario, 'o Administrador Geral encontra a empresa', item is not None, f'busca={busca}')
    if item:
        r.checar(cenario, 'a resposta NÃO traz local_status (perfil sem Unidade de referência)',
                 item.get('local_status') is None, f"local_status={item.get('local_status')}")
        r.checar(cenario, 'a resposta NÃO traz linked_units_count (não é item mascarado)',
                 item.get('linked_units_count') is None, f"linked_units_count={item.get('linked_units_count')}")


def c7_isolamento_entre_tenants(r):
    cenario = 'C7 · Isolamento entre tenants'

    _, busca = http('GET', f'/api/outsourced-companies/search?actor_user_id={USER_BETA}&q=Ômega')
    r.checar(cenario, 'a busca do tenant Beta NÃO alcança a empresa do Alfa',
             achar(busca.get('outsourced_companies', []), OSC_OMEGA) is None, f'busca={busca}')

    status, corpo = http('POST', f'/api/outsourced-companies/{OSC_OMEGA}/link',
                         corpo={'actor_user_id': USER_BETA})
    r.checar(cenario, 'vincular empresa de outro tenant é recusado', status in (403, 404),
             f'status={status} corpo={corpo}')

    status, corpo = http('GET', f'/api/employees/{EMP_BELTRANO}/unit-links?actor_user_id={USER_BETA}')
    r.checar(cenario, 'ler vínculos de colaborador de outro tenant é recusado', status in (403, 404),
             f'status={status} corpo={corpo}')

    status, corpo = http('GET', f'/api/employees/{EMP_BELTRANO}/unit-links?actor_user_id={USER_SUL}')
    r.checar(cenario, 'dentro do tenant, a Sul lê APENAS o vínculo da própria Unidade',
             status == 200 and [int(v['unit_id']) for v in corpo.get('unit_links', [])] == [UNIT_SUL],
             f'status={status} corpo={corpo}')


def main():
    if not os.environ.get('DATABASE_URL', '').startswith('postgres'):
        print('DATABASE_URL precisa apontar para PostgreSQL.')
        return 1
    print('Semeando dois tenants em PostgreSQL real...')
    semear()
    print(f'Subindo app.py em {BASE} ...')
    servidor = subir_servidor()
    resultado = Resultado()
    try:
        for cenario in (c1_empresa_multi_unidade, c2_colaborador_multi_unidade, c3_sem_heranca,
                        c4_arquivamento_local_independente, c5_reativacao_com_historico,
                        c6_null_nao_informado, c7_isolamento_entre_tenants):
            cenario(resultado)
    finally:
        servidor.terminate()
        servidor.wait(timeout=10)
    return 0 if resultado.imprimir() else 1


if __name__ == '__main__':
    sys.exit(main())
