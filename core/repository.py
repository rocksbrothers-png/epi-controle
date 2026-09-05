"""Repositório central: funções de DB e autorização compartilhadas entre módulos."""

from datetime import date
from typing import NamedTuple

from core.auth import ensure_company_access, ensure_permission
from core.roles import CERTIFICATION_READONLY_ROLE, normalize_role_name
from epi_backend.db import row_to_dict

# ── Contagem de usuários ──────────────────────────────────────────────────────

_BILLABLE_ROLES = (
    'general_admin',
    'registry_admin',
    'manager',
    'safety_tech',
    'buyer',
    'approver',
    'admin',
    'user',
)


def count_company_users(connection, company_id):
    placeholders = ','.join(['%s'] * len(_BILLABLE_ROLES))
    return connection.execute(
        f"SELECT COUNT(*) FROM users WHERE company_id = %s AND active = 1 AND role IN ({placeholders})",
        (company_id, *_BILLABLE_ROLES),
    ).fetchone()[0]


# ── Lookups simples ───────────────────────────────────────────────────────────

def get_company_by_id(connection, company_id):
    row = connection.execute(
        'SELECT id, name, user_limit, license_status, active, contract_end, addendum_enabled '
        'FROM companies WHERE id = %s',
        (company_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_employee_by_id(connection, employee_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, '
        'preferred_contact_channel, sector, role_name, admission_date, schedule_type, '
        f'tipo_vinculo, empresa_origem{_employee_legal_entity_column(connection)}'
        f'{_employee_outsourced_columns(connection)} FROM employees WHERE id = %s',
        (int(employee_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def _employee_legal_entity_column(connection) -> str:
    """`, legal_entity_id` quando a coluna Multi-CNPJ existir; vazio caso
    contrário (janela de migração / schema parcial)."""
    from epi_backend.db import table_columns
    return ', legal_entity_id' if 'legal_entity_id' in table_columns(connection, 'employees') else ''


def _employee_outsourced_columns(connection) -> str:
    """Colunas do vínculo com empresa terceirizada/prestadora (ADR-0002)
    quando o schema já está provisionado; vazio caso contrário (janela de
    migração / schema parcial), preservando retrocompatibilidade."""
    from epi_backend.db import table_columns
    if 'outsourced_company_id' not in table_columns(connection, 'employees'):
        return ''
    return (
        ', outsourced_company_id, service_contract_id, epi_responsibility_override, '
        'epi_responsibility_override_reason'
    )


def get_unit_by_id(connection, unit_id):
    row = connection.execute(
        'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = %s',
        (int(unit_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_epi_by_id(connection, epi_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, name, purchase_code, ca, active, '
        'unit_measure, glove_size, size, uniform_size, active_joinventure, scope_type '
        'FROM epis WHERE id = %s',
        (int(epi_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_active_jv_name(connection, unit_id):
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = %s AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),),
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


# ── Unidade operacional do ator ───────────────────────────────────────────────

def get_employee_current_unit(connection, employee_id):
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        return None
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT target_unit_id
        FROM employee_unit_movements
        WHERE employee_id = %s
          AND movement_type = 'temporary'
          AND start_date <= %s
          AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= %s
        ORDER BY start_date DESC, id DESC
        LIMIT 1
        ''',
        (int(employee_id), today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


def actor_operational_unit_id(connection, actor):
    """Unidade operacional atual do ator (Administrador Local/Gestor de EPI
    têm vínculo único com UMA unidade — nunca uma carteira; ver
    docs/PAPEIS_E_ATRIBUICOES.md). Vive aqui (não em
    modules.employees.service) para que módulos de domínio (legal_entities,
    units, employees) possam resolver o escopo do ator sem importar uns aos
    outros — a causa raiz do ciclo de import fechado por
    modules.legal_entities.service -> modules.employees.service (issue #148).

    Consulta direto com placeholders `?` (como o resto do projeto — o
    wrapper de Postgres os traduz para `%s`; sqlite não entende `%s` sem
    passar por esse wrapper) em vez de reaproveitar get_employee_by_id/
    get_employee_current_unit deste mesmo módulo, que usam `%s` fixo no
    texto da query — inconsistência pré-existente e fora do escopo desta
    correção, que quebraria com conexões sqlite diretas (usadas em vários
    testes) se reaproveitada aqui.
    """
    if not actor or actor.get('role') not in ('admin', 'user'):
        return None
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id:
        return None
    employee_id = int(linked_employee_id)
    employee_row = connection.execute(
        'SELECT unit_id FROM employees WHERE id = ?', (employee_id,)
    ).fetchone()
    if not employee_row:
        return None
    employee = row_to_dict(employee_row)
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT target_unit_id
        FROM employee_unit_movements
        WHERE employee_id = ?
          AND movement_type = 'temporary'
          AND start_date <= ?
          AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?
        ORDER BY start_date DESC, id DESC
        LIMIT 1
        ''',
        (employee_id, today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


# ── Bloqueio comercial ────────────────────────────────────────────────────────

def evaluate_company_block_status(connection, company_id, persist_expiration=True):
    company = get_company_by_id(connection, company_id)
    if not company:
        raise ValueError('Empresa vinculada não encontrada.')

    reasons = []
    today_iso = date.today().isoformat()
    contract_end = str(company.get('contract_end') or '').strip()
    license_status = str(company.get('license_status') or 'active').strip() or 'active'

    if contract_end and contract_end < today_iso:
        reasons.append('license_expired_by_contract')
        if persist_expiration and license_status != 'expired':
            connection.execute(
                'UPDATE companies SET license_status = %s WHERE id = %s',
                ('expired', company_id),
            )
            connection.commit()
            license_status = 'expired'

    if int(company.get('active') or 0) != 1:
        reasons.append('company_inactive')
    if license_status == 'suspended':
        reasons.append('license_suspended')
    if license_status == 'expired':
        reasons.append('license_expired_by_contract')

    active_users = count_company_users(connection, company_id)
    user_limit = int(company.get('user_limit') or 0)
    addendum_enabled = int(company.get('addendum_enabled') or 0) == 1
    if user_limit > 0 and active_users > user_limit and not addendum_enabled:
        reasons.append('usage_exceeds_contract')

    dedup = []
    for r in reasons:
        if r not in dedup:
            dedup.append(r)

    return {
        'company_id': int(company_id),
        'blocked': bool(dedup),
        'reasons': dedup,
        'license_status': license_status,
        'active_users': active_users,
        'user_limit': user_limit,
        'addendum_enabled': addendum_enabled,
        'contract_end': contract_end,
    }


def enforce_company_block_rules(connection, company_id):
    status = evaluate_company_block_status(connection, company_id, persist_expiration=True)
    if not status['blocked']:
        return
    reason = status['reasons'][0]
    if reason == 'company_inactive':
        raise PermissionError('Acesso bloqueado: empresa inativa.')
    if reason in ('license_suspended', 'license_expired_by_contract'):
        raise PermissionError('Acesso bloqueado: licença suspensa ou expirada.')
    if reason == 'usage_exceeds_contract':
        raise PermissionError('Acesso bloqueado: uso acima do limite contratado.')
    raise PermissionError('Acesso bloqueado por política comercial.')


# ── Usuários e autorização ────────────────────────────────────────────────────

def get_user_by_id(connection, user_id):
    row = connection.execute(
        'SELECT users.id, users.username, users.password, users.full_name, users.role, '
        'users.company_id, users.active, users.linked_employee_id, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, '
        'companies.logo_type '
        'FROM users LEFT JOIN companies ON companies.id = users.company_id '
        'WHERE users.id = %s',
        (user_id,),
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item['role'] = normalize_role_name(item.get('role'))
    if item.get('role') in ('admin', 'user') and item.get('linked_employee_id'):
        operational_unit_id = get_employee_current_unit(connection, int(item['linked_employee_id']))
        if operational_unit_id:
            item['operational_unit_id'] = operational_unit_id
    return item


# Política de senha temporária. Vive AQUI, e não em modules.auth.service,
# pelo mesmo motivo de `actor_operational_unit_id`: `require_actor` precisa
# consultá-la, e `core.repository -> modules.auth.service` fecha exatamente o
# ciclo de import da issue #148 (auth.service já importa deste módulo).
def get_user_password_policy(connection, user_id):
    """Estado da política de senha temporária do usuário.

    Retorna {'must_change': bool, 'expired': bool}. Tolerante a bases sem as
    colunas (pré-migração) — nesse caso a política fica inativa (não bloqueia
    ninguém), preservando o login dos usuários existentes.
    """
    from datetime import datetime
    from epi_backend.config import UTC
    try:
        row = connection.execute(
            'SELECT must_change_password, password_expires_at FROM users WHERE id = ?',
            (int(user_id),),
        ).fetchone()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            # Rollback que falha significa conexão já inutilizável: não há o que
            # desfazer, e levantar aqui esconderia a falha original (coluna
            # ausente em base pré-migração) atrás de uma secundária. O `return`
            # abaixo é o que importa — base sem as colunas mantém a política
            # inativa e PRESERVA o login dos usuários existentes.
            pass
        return {'must_change': False, 'expired': False}
    if not row:
        return {'must_change': False, 'expired': False}
    data = row_to_dict(row)
    must_change = int(data.get('must_change_password') or 0) == 1
    expires_raw = str(data.get('password_expires_at') or '').strip()
    expired = False
    if expires_raw:
        try:
            exp = datetime.fromisoformat(expires_raw)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            expired = datetime.now(UTC) > exp
        except Exception:
            expired = False
    return {'must_change': must_change, 'expired': expired}


class UnitScope(NamedTuple):
    """Unidade que o SERVIDOR resolveu para uma consulta, e de onde ela veio.

    `source` é o que permite ao chamador (e ao cliente) saber por que o
    recorte é o que é, sem deduzir:

    - `'actor'`   — perfil travado; veio de `actor_operational_unit_id`
    - `'selected'`— perfil livre; veio do `unit_id` pedido, já validado
    - `'none'`    — perfil livre sem seleção: visão corporativa

    `unit_id` é `None` exatamente quando `source == 'none'`. Nunca 0: zero não
    é unidade, e tratá-lo como "sem unidade" por ser falsy é a família de
    defeito que a fatia 1.1B eliminou do saldo de estoque.
    """

    unit_id: int | None
    source: str
    locked: bool


def resolve_unit_scope(connection, actor, requested_unit_id=None, *, denial_message=None):
    """Contexto de Unidade de uma consulta — ponto ÚNICO de resolução.

    Existia como sete cópias de `scope_unit_id or query.get('unit_id')`
    espalhadas por `modules/stock/routes.py`. Cópias da mesma regra divergem no
    primeiro ajuste feito num lado só, e nenhuma delas validava o `unit_id`
    recebido do cliente.

    Regras, nesta ordem:

    1. **Perfil travado** (`admin`/`user`): a unidade vem de
       `actor_operational_unit_id` — que já honra movimento temporário vigente
       — e o `unit_id` do cliente é **descartado**, não recusado. Recusar
       transformaria um cliente desatualizado em erro; descartar mantém a
       autorização no servidor sem quebrar ninguém.
    2. **Perfil travado sem unidade**: `PermissionError`. Fail-closed — nunca
       cai para a empresa inteira.
    3. **Perfil livre com `unit_id`**: a unidade precisa existir e pertencer à
       empresa do ator, senão `ValueError` (→ 400). Antes, o isolamento
       dependia da composição incidental de dois filtros: nada vazava, mas a
       garantia não estava escrita em lugar nenhum.
    4. **Perfil livre sem `unit_id`**: visão corporativa (`None`).

    `master_admin` opera cross-tenant por desenho e não tem empresa própria:
    a validação do item 3 é pulada para ele, porque não há tenant contra o qual
    comparar.

    `denial_message` só troca o texto do item 2, para que cada rota continue
    dizendo ao usuário o que ele não conseguiu fazer ("para consultar estoque",
    "para movimentar estoque"). A regra é a mesma; a mensagem é do chamador.
    """
    role = str((actor or {}).get('role') or '')
    locked = role in ('admin', 'user')

    if locked:
        unit_id = actor_operational_unit_id(connection, actor)
        if not unit_id:
            raise PermissionError(denial_message or 'Perfil sem unidade operacional ativa.')
        return UnitScope(int(unit_id), 'actor', True)

    pedido = str(requested_unit_id or '').strip()
    if not pedido:
        return UnitScope(None, 'none', False)
    try:
        pedido_id = int(pedido)
    except (TypeError, ValueError):
        raise ValueError('Unidade inválida.')
    if pedido_id <= 0:
        raise ValueError('Unidade inválida.')

    if role != 'master_admin':
        row = connection.execute(
            'SELECT company_id FROM units WHERE id = ?', (pedido_id,)
        ).fetchone()
        if not row:
            raise ValueError('Unidade não encontrada.')
        unidade = row_to_dict(row)
        empresa_ator = str(actor.get('company_id') or '').strip()
        empresa_unidade = str(unidade.get('company_id') or '').strip()
        # Empresa ausente em QUALQUER dos lados nega. Comparar direto faria
        # `'' == ''` casar: um perfil sem empresa alcançaria toda unidade órfã,
        # e vice-versa. "Desconhecido" nunca é "igual".
        if not empresa_ator or not empresa_unidade or empresa_unidade != empresa_ator:
            raise ValueError('Unidade não pertence à empresa do usuário.')

    return UnitScope(pedido_id, 'selected', False)


class UnitSelection(NamedTuple):
    """Escopo de Unidade resolvido pelo SERVIDOR, com a lista do seletor.

    Estende `UnitScope` com o que o cliente precisa para DESENHAR o seletor
    sem reconstruir autorização nenhuma. Existe separada porque `UnitScope`
    responde "qual Unidade?" e é usada em caminhos que não têm seletor
    (entrega, movimentação); esta responde também "quais o ator poderia
    escolher?".

    `source` ganha um quarto valor em relação a `UnitScope`:

    - `'actor'`          — perfil travado; veio de `actor_operational_unit_id`
    - `'selected'`       — Unidade escolhida explicitamente, já validada
    - `'purchase_scope'` — Comprador/Aprovador SEM seleção: a visão é a
      carteira de `purchase_role_unit_links` ("Todas as minhas Unidades")
    - `'none'`           — visão corporativa legítima de quem tem esse direito

    O quarto valor não é enfeite. Sem ele, Comprador sem seleção cairia em
    `'none'`, que significa "empresa inteira" — exatamente o vazamento que
    esta fatia existe para impedir. `'none'` e `'purchase_scope'` têm o mesmo
    `unit_id` (`None`) e significados opostos.

    `allowed_unit_ids` é `None` quando NÃO há restrição de carteira (perfis
    administrativos) e uma tupla quando há. **Tupla vazia significa carteira
    vazia: nenhum resultado.** A diferença entre `None` e `()` nunca pode ser
    testada por truthiness — `if not allowed_unit_ids` confundiria "sem
    restrição" com "não pode ver nada", que é a família de defeito que já
    custou caro no saldo de estoque. Use `is None`, ou a propriedade
    `blocks_everything`.
    """

    unit_id: int | None
    source: str
    locked: bool
    allowed_unit_ids: tuple[int, ...] | None
    allows_all_units: bool

    @property
    def blocks_everything(self) -> bool:
        """Carteira existente e vazia: o ator não enxerga Unidade nenhuma."""
        return self.allowed_unit_ids is not None and not self.allowed_unit_ids

    def permits(self, unit_id) -> bool:
        """A Unidade está no direito do ator? Sem restrição ⇒ sempre sim."""
        if self.allowed_unit_ids is None:
            return True
        return int(unit_id) in self.allowed_unit_ids


def selectable_units(unidades, selection: UnitSelection):
    """As Unidades da lista que o ator pode ESCOLHER no seletor.

    Ponto único da pergunta "o que aparece no seletor?". Antes desta função a
    resposta existia em dois lugares: aqui, como `UnitSelection.permits`, e no
    dashboard, como `_unidade_selecionavel` — duas implementações da mesma
    regra, que divergiriam no primeiro ajuste feito num lado só. É o mesmo
    defeito que a 1.1D-C4 desfez entre Dart e JS.

    Toda a decisão está em `permits`, e por isso ela vale para os quatro casos
    sem `if` de perfil nenhum aqui:

        perfil travado      allowed_unit_ids = (própria,)  → só a própria
        carteira vazia      allowed_unit_ids = ()          → NENHUMA
        carteira preenchida allowed_unit_ids = (a, b)      → só a carteira
        perfil livre        allowed_unit_ids = None        → todas do tenant

    A linha que importa é a segunda. Carteira vazia devolve lista vazia, nunca
    a empresa inteira — e é por isso que `permits` testa `is None` em vez de
    truthiness: `if not allowed_unit_ids` faria `()` e `None` se comportarem
    igual, transformando "não pode ver nada" em "pode ver tudo".

    A lista de entrada já vem recortada por tenant (`fetch_units`); aqui só se
    aplica o direito do ator sobre ela.
    """
    return [
        unidade for unidade in unidades
        if selection.permits(_unit_id_of(unidade)) and _unit_id_of(unidade)
    ]


def _unit_id_of(unidade):
    try:
        return int((unidade or {}).get('id'))
    except (TypeError, ValueError):
        return 0


# Perfis cuja visão de Compras é a carteira de `purchase_role_unit_links`.
# Administrador Geral e de Registro NÃO entram: a Unidade deles é escolha, não
# vínculo (ver `get_actor_purchase_unit_scope`).
PURCHASE_CARTEIRA_ROLES = ('buyer', 'approver')


def resolve_purchase_unit_scope(
    connection, actor, requested_unit_id=None, *, purchase_units_loader,
    operational_unit_loader=None, denial_message=None,
):
    """Escopo de Unidade em Compras — ponto ÚNICO, inclusive para o seletor.

    `purchase_units_loader(connection, actor)` devolve a carteira do ator
    (`get_actor_purchase_unit_scope`). Entra por injeção, e não por import,
    porque `core.repository` não pode importar `modules.purchases` sem
    reabrir o ciclo fechado pela issue #148 — mesmo motivo pelo qual
    `build_dashboard_summary` recebe `fetch_units`/`fetch_epis`.

    Regras, nesta ordem:

    1. **Perfil travado** (`admin`/`user`): Unidade de
       `actor_operational_unit_id`, `unit_id` do cliente descartado, e nunca
       a opção "Todas". Sem unidade ⇒ `PermissionError` (fail-closed).
    2. **Comprador/Aprovador**: só as Unidades da carteira. Carteira vazia
       não vira empresa inteira — devolve `allowed_unit_ids=()`, que o
       chamador honra como "nenhum resultado". "Todas as minhas Unidades" só
       é oferecida a partir de duas Unidades; com uma só, ela é
       pré-selecionada.
    3. **Demais perfis livres** (Administrador Geral/Registro,
       `master_admin`): todas as Unidades do tenant, com "Todas".

    A Unidade pedida é validada em duas etapas, com erros diferentes de
    propósito: pertencer ao tenant é `ValueError` (→ 400, identificador
    inválido para este contexto); estar fora do direito do ator é
    `PermissionError` (→ 403, identificador válido que ele não pode usar).
    Colapsar os dois num só esconderia de um Comprador a diferença entre
    "essa Unidade não existe aqui" e "existe, mas não é sua".
    """
    role = str((actor or {}).get('role') or '')

    if role in ('admin', 'user'):
        # `operational_unit_loader` existe para que o chamador que JÁ resolveu
        # a unidade do ator (para a própria guarda de fail-closed) não a
        # resolva de novo aqui. Duas resoluções da mesma coisa é como as
        # variantes de escopo nascem: basta uma delas passar a honrar uma
        # regra que a outra ignora.
        resolver = operational_unit_loader or actor_operational_unit_id
        unit_id = resolver(connection, actor)
        if not unit_id:
            raise PermissionError(denial_message or 'Perfil sem unidade operacional ativa.')
        return UnitSelection(int(unit_id), 'actor', True, (int(unit_id),), False)

    if role == CERTIFICATION_READONLY_ROLE:
        # Identidade técnica da certificação (#313), com escopo ENUMERADO.
        #
        # Sem este ramo o papel cairia no `else` lá embaixo, que devolve
        # `allowed_unit_ids = None` — "sem restrição" — e passaria a depender
        # inteiramente de `fetch_units` recortar por `company_id`. O isolamento
        # entre tenants viraria efeito colateral de outra função, exatamente o
        # que não se quer numa credencial que roda sozinha no CI.
        #
        # Enumerar tem três consequências desejadas: o vínculo com o tenant
        # passa a ser valor de retorno e não efeito de terceiro; afrouxar
        # `fetch_units` amanhã não amplia este papel; e conta sem empresa
        # devolve `()`, que é `blocks_everything` — fail-closed alto e claro,
        # em vez de alcançar unidade órfã.
        #
        # `allows_all_units` é False de propósito: perfil somente-leitura não
        # tem o que fazer com "Todas". E `requested_unit_id` não é honrado
        # aqui porque o papel não alcança nenhuma rota de Compras — não há
        # seleção a validar, só a lista do seletor.
        empresa = str((actor or {}).get('company_id') or '').strip()
        if not empresa:
            return UnitSelection(None, 'certification', False, (), False)
        linhas = connection.execute(
            'SELECT id FROM units WHERE company_id = ? ORDER BY id', (empresa,)
        ).fetchall()
        permitidas = tuple(int(row_to_dict(linha)['id']) for linha in linhas)
        return UnitSelection(None, 'certification', False, permitidas, False)

    carteira = None
    if role in PURCHASE_CARTEIRA_ROLES:
        carregada = purchase_units_loader(connection, actor)
        # `get_actor_purchase_unit_scope` devolve `None` para "nenhum vínculo".
        # Para Comprador/Aprovador isso É a carteira vazia, não "sem
        # restrição" — a normalização acontece aqui, uma vez, em vez de em
        # cada chamador.
        carteira = tuple(int(u) for u in (carregada or ()))
        if not carteira:
            return UnitSelection(None, 'purchase_scope', False, (), False)

    permite_todas = carteira is None or len(carteira) > 1

    pedido = str(requested_unit_id or '').strip()
    if not pedido:
        if carteira is not None and len(carteira) == 1:
            # Uma única Unidade autorizada: já é a visão, não há o que escolher.
            return UnitSelection(carteira[0], 'selected', False, carteira, False)
        origem = 'purchase_scope' if carteira is not None else 'none'
        return UnitSelection(None, origem, False, carteira, permite_todas)

    try:
        pedido_id = int(pedido)
    except (TypeError, ValueError):
        raise ValueError('Unidade inválida.')
    if pedido_id <= 0:
        raise ValueError('Unidade inválida.')

    if role != 'master_admin':
        row = connection.execute(
            'SELECT company_id FROM units WHERE id = ?', (pedido_id,)
        ).fetchone()
        if not row:
            raise ValueError('Unidade não encontrada.')
        unidade = row_to_dict(row)
        empresa_ator = str(actor.get('company_id') or '').strip()
        empresa_unidade = str(unidade.get('company_id') or '').strip()
        # Empresa ausente em QUALQUER dos lados nega — "desconhecido" nunca é
        # "igual". Mesma regra de `resolve_unit_scope`.
        if not empresa_ator or not empresa_unidade or empresa_unidade != empresa_ator:
            raise ValueError('Unidade não pertence à empresa do usuário.')

    if carteira is not None and pedido_id not in carteira:
        raise PermissionError('Unidade fora das unidades de compras vinculadas ao usuário.')

    return UnitSelection(pedido_id, 'selected', False, carteira, permite_todas)


def require_actor(connection, actor_user_id, *, allow_password_change_pending=False):
    """Ator válido para uma operação autenticada.

    `allow_password_change_pending` é a exceção EXPLÍCITA ao bloqueio de senha
    temporária. Fica como parâmetro, e não como lista de rotas permitidas, por
    dois motivos: uma lista de strings envelhece calada quando alguém renomeia
    uma rota, e a exceção precisa estar visível em quem a usa — não num arquivo
    de configuração distante de onde a decisão importa.

    Hoje só `/api/auth/me` a usa: é a rota que informa ao cliente POR QUE ele
    está bloqueado. Negá-la deixaria o app sem meio de descobrir para onde ir
    depois de um restart com token já emitido.
    """
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    actor['role'] = normalize_role_name(actor.get('role'))
    if actor.get('role') != 'master_admin' and actor.get('company_id'):
        enforce_company_block_rules(connection, int(actor['company_id']))
    if not allow_password_change_pending:
        _deny_while_password_change_pending(connection, actor)
    return actor


def _deny_while_password_change_pending(connection, actor):
    """Bloqueia operações autenticadas enquanto a senha temporária não for trocada.

    Aqui, e não no login: o login PRECISA suceder para o cliente receber o
    token e conseguir chamar `/api/change-password`. O que não pode é o token
    servir para o resto — que era exatamente o furo, já que a obrigatoriedade
    vivia só no redirect da UI e qualquer chamada direta à API passava por
    cima.

    `require_actor` é o ponto certo porque `authorize_action` e
    `authorize_action_any` passam os dois por ele: uma checagem cobre as 242
    chamadas dos 21 módulos, sem marcar rota a rota.

    `/api/change-password` NÃO passa por aqui (usa `get_user_by_id` direto), e
    é por isso que o caminho de saída não se tranca sozinho. Há teste para
    isso — a garantia não pode depender de alguém lembrar.

    Base pré-migração (colunas ausentes) devolve `must_change: False` e não
    bloqueia ninguém: fail-open deliberado, para uma migration não aplicada não
    derrubar o sistema inteiro.
    """
    from core.security import PasswordChangeRequiredError

    if get_user_password_policy(connection, int(actor['id']))['must_change']:
        raise PasswordChangeRequiredError()


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def authorize_action_any(connection, actor_user_id, actions, company_id=None):
    """Como `authorize_action`, mas aceita qualquer uma das permissões em
    `actions` — usado quando dois perfis distintos alcançam a mesma rota por
    permissões técnicas diferentes (ex.: Administrador Geral via
    employees:create, Administrador Local/Gestor de EPI via
    employees:create_simplified, ambos operando Empresas Terceirizadas
    dentro do próprio escopo). Levanta o erro da última permissão tentada
    quando nenhuma é concedida."""
    actor = require_actor(connection, actor_user_id)
    error = PermissionError('Nenhuma permissão informada.')
    for action in actions:
        try:
            ensure_permission(actor, action)
            break
        except PermissionError as exc:
            error = exc
    else:
        raise error
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def require_master_actor(connection, actor_user_id):
    actor = authorize_action(connection, actor_user_id, 'commercial:view')
    if actor['role'] != 'master_admin':
        raise PermissionError('Apenas o Administrador Master pode alterar a marca do sistema.')
    return actor
