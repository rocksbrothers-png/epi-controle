"""Serviços de Empresa Terceirizada/Prestadora — Cadastro Simplificado (ADR-014).

``outsourced_companies`` é uma tabela de referência pequena, isolada por
tenant (``company_id``): NÃO é um tenant, não tem plano/billing/login
próprio, não é uma segunda base de colaboradores. Modela a empresa externa
que empresta mão de obra para a operação (Terceirizada, Prestadora de
Serviço, ou Outro) — no mesmo padrão que ``authorized_suppliers`` já valida
em produção para um relacionamento de negócio diferente (compra de
material, não fornecimento de mão de obra).

``service_contracts`` permite múltiplos contratos (unidades/períodos
diferentes) para a mesma empresa terceirizada, sem duplicar seu cadastro.
Cada contrato pode sobrescrever a responsabilidade padrão de fornecimento
de EPI da empresa, com motivo auditável.

Este módulo cobre apenas a fundação (PR 1 da sequência aprovada): CRUD
escopado por tenant, normalização/unicidade de CNPJ, contratos. Integração
com o fluxo de entrega (snapshot histórico), relatórios e ressarcimento
ficam para PRs seguintes — ver docs/adr/adr-014-terceirizados.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from modules.commercial.service import only_digits, validate_cnpj

UTC = timezone.utc

# Valores técnicos estáveis (inglês) — condição vinculante da aprovação:
# rótulo em português só na camada de UI, nunca gravado na coluna.
COMPANY_KINDS: tuple[str, ...] = ('outsourced', 'service_provider', 'other_contracted')

EPI_RESPONSIBILITIES: tuple[str, ...] = (
    'Empresa Contratante',
    'Empresa Terceirizada',
    'Empresa Prestadora de Serviço',
    'Responsabilidade Compartilhada',
    'Conforme Contrato',
    'Não Definido',
)

REGISTRATION_MODES: tuple[str, ...] = ('simplified', 'standard')
REGISTRATION_STATUSES: tuple[str, ...] = ('pending_completion', 'complete', 'inactive', 'archived')

REIMBURSEMENT_STATUSES: tuple[str, ...] = (
    'Não Aplicável',
    'Pendente de Análise',
    'Passível de Ressarcimento',
    'Apta para Cobrança',
    'Incluída em Relatório',
    'Ressarcida',
    'Contestada',
    'Dispensada',
)

_SELECT_COLUMNS = (
    'id, company_id, unit_id, legal_name, trade_name, cnpj, cnpj_normalized, company_kind, '
    'epi_responsibility, registration_mode, registration_status, status, promoted_at, '
    'created_by_user_id, created_at, updated_at'
)

_CONTRACT_SELECT_COLUMNS = (
    'id, company_id, outsourced_company_id, unit_id, contract_ref, service_order_ref, start_date, end_date, '
    'epi_responsibility_override, override_reason, status, created_by_user_id, created_at, updated_at'
)


def outsourced_companies_ready(connection) -> bool:
    """Indica se o schema desta feature já está provisionado. Durante a
    janela de migração — e em fixtures de schema parcial — chamadas ao
    módulo devem checar isto e degradar graciosamente (subpasta oculta por
    módule_visibility de qualquer forma cobre o caso normal)."""
    from epi_backend.db import table_exists
    return table_exists(connection, 'outsourced_companies')


def normalize_company_kind(value) -> str:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in COMPANY_KINDS else 'outsourced'


def normalize_epi_responsibility(value) -> str:
    value = str(value or '').strip()
    return value if value in EPI_RESPONSIBILITIES else 'Conforme Contrato'


def normalize_registration_mode(value) -> str:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in REGISTRATION_MODES else 'simplified'


def normalize_registration_status(value) -> str:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in REGISTRATION_STATUSES else 'pending_completion'


class DuplicateOutsourcedCompanyError(ValueError):
    """CNPJ já cadastrado no tenant (ADR-0002 §12 — cadastro corporativo é
    único por tenant, nunca duplicado por Unidade). Carrega o id do
    registro já existente para a rota oferecer "Vincular à minha Unidade"
    em vez de só um erro genérico."""

    def __init__(self, existing_company_id, message):
        super().__init__(message)
        self.existing_company_id = int(existing_company_id)


def find_outsourced_company_by_cnpj(connection, company_id, cnpj_normalized, *, exclude_id=None):
    """Empresa terceirizada já cadastrada no tenant com este CNPJ, se
    houver — usado tanto na validação de duplicidade quanto na busca por
    CNPJ do fluxo de vinculação."""
    if not cnpj_normalized:
        return None
    row = connection.execute(
        'SELECT id FROM outsourced_companies WHERE company_id = ? AND cnpj_normalized = ? '
        + ('AND id <> ? ' if exclude_id else '')
        + 'LIMIT 1',
        (company_id, cnpj_normalized, exclude_id) if exclude_id else (company_id, cnpj_normalized),
    ).fetchone()
    return int(row_to_dict(row)['id']) if row else None


def search_outsourced_companies_by_name(connection, company_id, query, *, exclude_id=None, limit=10):
    """Correspondências por razão social/nome fantasia (substring,
    case-insensitive) — usado para alertar sobre possível duplicata quando
    o Cadastro Simplificado ainda não tem CNPJ (sem CNPJ, `find_outsourced_
    company_by_cnpj` não tem o que comparar) e para a busca manual do fluxo
    de vinculação. Nunca bloqueia: quem chama decide se avisa ou impede."""
    term = f'%{str(query or "").strip().lower()}%'
    if term == '%%':
        return []
    sql = (
        f'SELECT {_SELECT_COLUMNS} FROM outsourced_companies '  # noqa: S608
        'WHERE company_id = ? AND (LOWER(legal_name) LIKE ? OR LOWER(trade_name) LIKE ?) '
    )
    params = [company_id, term, term]
    if exclude_id:
        sql += 'AND id <> ? '
        params.append(exclude_id)
    rows = connection.execute(sql + 'ORDER BY legal_name LIMIT ?', (*params, limit)).fetchall()
    return [row_to_dict(row) for row in rows]


def mask_cnpj(cnpj) -> str:
    """Máscara padrão para CNPJ de empresa ainda não vinculada à Unidade do
    ator (ADR-0002 §12) — sem política de mascaramento pré-existente no
    sistema (nenhuma outra tela mascara CNPJ), então este é o padrão
    escolhido para esta feature: mantém os 2 primeiros e os 2 últimos
    dígitos, mascara o resto. CNPJ vazio (Cadastro Simplificado sem CNPJ
    ainda) permanece vazio — não há nada para mascarar."""
    digits = only_digits(str(cnpj or ''))
    if len(digits) != 14:
        return ''
    return f'{digits[:2]}.***.***/****-{digits[-2:]}'


def validate_outsourced_company_payload(connection, payload, company_id, entity_id=None):
    """Valida e normaliza o payload de uma empresa terceirizada/prestadora.

    CNPJ é opcional no Cadastro Simplificado (o pedido inicial pode ser
    emergencial, sem CNPJ em mãos) — quando informado, precisa ser válido e
    único dentro do tenant. Razão social é sempre obrigatória.
    """
    payload = payload or {}
    legal_name = str(payload.get('legal_name') or '').strip()
    if not legal_name:
        raise ValueError('Razão social é obrigatória.')

    raw_cnpj = str(payload.get('cnpj') or '').strip()
    if raw_cnpj:
        cnpj = validate_cnpj(raw_cnpj)
        cnpj_normalized = only_digits(cnpj)
        duplicate_id = find_outsourced_company_by_cnpj(connection, company_id, cnpj_normalized, exclude_id=entity_id)
        if duplicate_id:
            raise DuplicateOutsourcedCompanyError(
                duplicate_id, 'Já existe uma empresa terceirizada com este CNPJ neste tenant.'
            )
    else:
        cnpj = ''
        cnpj_normalized = ''

    registration_mode = normalize_registration_mode(payload.get('registration_mode'))
    registration_status = normalize_registration_status(payload.get('registration_status'))
    if registration_mode == 'standard' and not cnpj:
        raise ValueError('CNPJ é obrigatório para o Cadastro Padrão.')

    return {
        'company_id': int(company_id),
        'legal_name': legal_name,
        'trade_name': str(payload.get('trade_name') or '').strip(),
        'cnpj': cnpj,
        'cnpj_normalized': cnpj_normalized,
        'company_kind': normalize_company_kind(payload.get('company_kind')),
        'epi_responsibility': normalize_epi_responsibility(payload.get('epi_responsibility')),
        'registration_mode': registration_mode,
        'registration_status': registration_status,
        # `status` (ciclo de vida: active/archived/...) NÃO é aceito do
        # payload do cliente (ADR-0002 §10.4) — só as rotas de arquivar/
        # restaurar/expurgar (core.archival) mudam esse campo.
    }


def create_outsourced_company(connection, payload, company_id, actor_user_id=None, unit_id=None):
    """``unit_id``, quando informado, vira a Unidade de ORIGEM — gravada
    aqui uma única vez, nunca mais alterável (ver ``update_outsourced_company``).
    A Unidade de origem já nasce com seu próprio vínculo ativo em
    ``outsourced_company_unit_links`` (ADR-0002 §12): quem cadastra não
    precisa de um segundo passo para começar a usar a própria empresa."""
    validated = validate_outsourced_company_payload(connection, payload, company_id)
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO outsourced_companies (company_id, unit_id, legal_name, trade_name, cnpj, '
        'cnpj_normalized, company_kind, epi_responsibility, registration_mode, '
        'registration_status, status, created_by_user_id, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            validated['company_id'], int(unit_id) if unit_id else None,
            validated['legal_name'], validated['trade_name'],
            validated['cnpj'], validated['cnpj_normalized'], validated['company_kind'],
            validated['epi_responsibility'], validated['registration_mode'],
            validated['registration_status'], 'active',
            int(actor_user_id) if actor_user_id else None, now_iso, now_iso,
        ),
    )
    entity_id = int(cursor.lastrowid)
    connection.commit()
    if unit_id:
        create_outsourced_company_unit_link(connection, entity_id, company_id, unit_id, actor_user_id)
    return entity_id


def update_outsourced_company(connection, entity_id, payload, company_id):
    """Unidade de origem (``outsourced_companies.unit_id``) é imutável após
    a criação (ADR-0002 §12) — nunca aceita de payload, nem de Administrador
    Geral: é só metadado histórico de quem cadastrou primeiro. Quem usa a
    empresa em cada Unidade é ``outsourced_company_unit_links``, gerido
    pelas suas próprias rotas de vínculo (create/activate/deactivate)."""
    validated = validate_outsourced_company_payload(connection, payload, company_id, entity_id=entity_id)
    now_iso = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE outsourced_companies SET legal_name = ?, trade_name = ?, cnpj = ?, '
        'cnpj_normalized = ?, company_kind = ?, epi_responsibility = ?, registration_mode = ?, '
        'registration_status = ?, updated_at = ? WHERE id = ? AND company_id = ?',
        (
            validated['legal_name'], validated['trade_name'], validated['cnpj'],
            validated['cnpj_normalized'], validated['company_kind'], validated['epi_responsibility'],
            validated['registration_mode'], validated['registration_status'],
            now_iso, int(entity_id), int(company_id),
        ),
    )
    connection.commit()


# ── Escopo por Unidade (ADR-0002 §10.5) ────────────────────────────────────
# Descentraliza o cadastro de Empresas Terceirizadas/Prestadoras para
# Administrador Local/Gestor de EPI, sem novo mecanismo de autorização:
# reaproveita o vínculo de Unidade operacional única já usado pelo Cadastro
# de Colaboradores simplificado (actor_operational_unit_id, em
# core/repository.py — vive lá, não em modules.employees.service, pelo
# mesmo motivo de ciclo de import já documentado ali) e o gate de módulo
# por Unidade já existente (modules.settings.service.
# ensure_module_enabled_for_unit, chamado nas rotas antes de qualquer
# escrita). Os demais perfis (general_admin/registry_admin/master_admin,
# checados por employees:create/update) não são restritos por Unidade —
# `unit_id=None` preserva o comportamento anterior a esta extensão (empresa
# "de todo o tenant").

def resolve_outsourced_company_unit_id(connection, actor, payload, company_id):
    """Resolve o unit_id de uma Empresa Terceirizada a partir do ator e do
    payload. Administrador Local/Gestor de EPI são sempre forçados à
    própria Unidade operacional — o valor do payload (se vier) é ignorado,
    exatamente como em
    modules.employees.service.ensure_actor_unit_scope_for_target: não dá
    para burlar o escopo mandando um unit_id diferente. Os demais perfis
    podem informar uma Unidade (empresa passa a ser "daquela Unidade") ou
    omitir (empresa "do tenant", sem Unidade).
    """
    from core.repository import actor_operational_unit_id
    if actor.get('role') in ('admin', 'user'):
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if not scope_unit_id:
            raise PermissionError('Seu perfil não possui unidade operacional ativa.')
        return int(scope_unit_id)
    raw = (payload or {}).get('unit_id')
    if raw in (None, '', 0, '0'):
        return None
    unit_id = int(raw)
    unit = connection.execute(
        'SELECT id FROM units WHERE id = ? AND company_id = ? LIMIT 1', (unit_id, company_id),
    ).fetchone()
    if not unit:
        raise ValueError('Unidade não encontrada nesta empresa.')
    return unit_id


def ensure_actor_outsourced_company_scope(connection, actor, entity):
    """Administrador Local/Gestor de EPI só podem ver/editar/arquivar o
    registro corporativo de uma Empresa Terceirizada quando a própria
    Unidade operacional está VINCULADA a ela (``outsourced_company_unit_links``)
    — desde a extensão de compartilhamento por tenant (ADR-0002 §12), a
    Unidade de origem (``entity['unit_id']``) é só metadado histórico e não
    concede nem restringe mais nada sozinha: o vínculo explícito ("Vincular
    à minha Unidade") é a única autoridade. Os demais perfis, já filtrados
    por employees:create/update (mais amplo), não são restritos aqui."""
    if actor.get('role') not in ('admin', 'user'):
        return
    from core.repository import actor_operational_unit_id
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if not scope_unit_id or not fetch_outsourced_company_unit_link(connection, entity['id'], scope_unit_id):
        raise PermissionError(
            'Operação permitida somente para Empresas Terceirizadas vinculadas à sua Unidade operacional.'
        )


# ── Vínculo por Unidade — compartilhamento por tenant (ADR-0002 §12) ──────
# O cadastro corporativo (``outsourced_companies``) é único por tenant,
# identificado prioritariamente pelo CNPJ (``find_outsourced_company_by_cnpj``
# acima). A Unidade de origem só registra quem cadastrou primeiro — nunca
# mais muda (``create_outsourced_company``/``update_outsourced_company``).
# Qualquer Unidade do tenant localiza o cadastro existente (por CNPJ ou
# nome — ``find_outsourced_company_by_cnpj``/``search_outsourced_companies_by_name``)
# e cria seu próprio vínculo aqui, sem duplicar a empresa e sem herdar
# vínculo/contratos/colaboradores de outra Unidade (isolamento garantido
# por ``ensure_actor_outsourced_company_scope`` acima, que só concede
# acesso de escrita quando existe uma linha aqui para a Unidade do ator).

_UNIT_LINK_SELECT_COLUMNS = (
    'id, company_id, outsourced_company_id, unit_id, local_status, contract_number, '
    'contract_start_date, contract_end_date, local_responsible_id, cost_center_ref, notes, '
    'activated_at, deactivated_at, deactivated_by_user_id, deactivation_reason, '
    'created_by_user_id, updated_by_user_id, created_at, updated_at'
)


def fetch_outsourced_company_unit_link(connection, outsourced_company_id, unit_id):
    row = connection.execute(
        f'SELECT {_UNIT_LINK_SELECT_COLUMNS} FROM outsourced_company_unit_links '  # noqa: S608
        'WHERE outsourced_company_id = ? AND unit_id = ? LIMIT 1',
        (int(outsourced_company_id), int(unit_id)),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_outsourced_company_unit_link_by_id(connection, link_id):
    row = connection.execute(
        f'SELECT {_UNIT_LINK_SELECT_COLUMNS} FROM outsourced_company_unit_links WHERE id = ?',  # noqa: S608
        (int(link_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_outsourced_company_unit_links(connection, outsourced_company_id):
    """Todos os vínculos (de todas as Unidades) de uma empresa — usado só
    pelos perfis não escopados por Unidade (Geral/Registro/Master), nunca
    exposto a Administrador Local/Gestor de EPI (que só veem o próprio)."""
    rows = connection.execute(
        f'SELECT {_UNIT_LINK_SELECT_COLUMNS} FROM outsourced_company_unit_links '  # noqa: S608
        'WHERE outsourced_company_id = ? ORDER BY created_at',
        (int(outsourced_company_id),),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_outsourced_company_unit_link(connection, outsourced_company_id, company_id, unit_id, actor_user_id):
    """Ação "Vincular à minha unidade" — idempotente: vincular de novo uma
    empresa já vinculada só devolve o vínculo existente, sem duplicar linha
    nem reativar um vínculo que a própria Unidade desativou de propósito."""
    existing = fetch_outsourced_company_unit_link(connection, outsourced_company_id, unit_id)
    if existing:
        return int(existing['id'])
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO outsourced_company_unit_links (company_id, outsourced_company_id, unit_id, '
        'local_status, activated_at, created_by_user_id, updated_by_user_id, created_at, updated_at) '
        "VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)",
        (
            int(company_id), int(outsourced_company_id), int(unit_id), now_iso,
            int(actor_user_id) if actor_user_id else None,
            int(actor_user_id) if actor_user_id else None, now_iso, now_iso,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def set_outsourced_company_unit_link_status(connection, link_id, company_id, status, actor_user_id, reason=''):
    """Ativa/desativa o vínculo LOCAL de uma Unidade — nunca o cadastro
    corporativo (``outsourced_companies.status``, arquivamento via
    ``core.archival``, ADR-0002 §10.4). Desativar aqui não afeta nenhuma
    outra Unidade vinculada à mesma empresa."""
    normalized = 'active' if str(status or '').strip().lower() == 'active' else 'inactive'
    now_iso = datetime.now(UTC).isoformat()
    if normalized == 'active':
        connection.execute(
            "UPDATE outsourced_company_unit_links SET local_status = 'active', activated_at = ?, "
            'deactivated_at = NULL, deactivated_by_user_id = NULL, deactivation_reason = \'\', '
            'updated_by_user_id = ?, updated_at = ? WHERE id = ? AND company_id = ?',
            (now_iso, int(actor_user_id) if actor_user_id else None, now_iso, int(link_id), int(company_id)),
        )
    else:
        connection.execute(
            "UPDATE outsourced_company_unit_links SET local_status = 'inactive', deactivated_at = ?, "
            'deactivated_by_user_id = ?, deactivation_reason = ?, updated_by_user_id = ?, updated_at = ? '
            'WHERE id = ? AND company_id = ?',
            (
                now_iso, int(actor_user_id) if actor_user_id else None, str(reason or '').strip(),
                int(actor_user_id) if actor_user_id else None, now_iso, int(link_id), int(company_id),
            ),
        )
    connection.commit()
    return normalized


def ensure_actor_can_edit_outsourced_company_corporate_fields(actor, entity):
    """Depois que uma Empresa Terceirizada é promovida ao Cadastro Padrão
    (``registration_mode == 'standard'``), editar dados corporativos (razão
    social, nome fantasia, CNPJ, tipo) e arquivar/reativar o registro
    passam a ser exclusivos de Administrador Geral/de Registro — Master
    fica de fora por doutrina já documentada (PAPEIS_E_ATRIBUICOES.md #1,
    "Master não deve reter permissão permanente de execução operacional");
    `master_admin` já não tem `PERM_EMPLOYEES_UPDATE`
    (`MASTER_ADMIN_OPERATIONAL_EXCLUSIONS`, core/permissions.py), então
    `general_admin`/`registry_admin` já é exatamente o grupo certo, sem
    permissão nova. Enquanto `simplified`, nada muda — mesmo grupo de hoje
    (`employees:update`/`_simplified`, verificado no piso técnico da rota).
    """
    if entity.get('registration_mode') != 'standard':
        return
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError(
            'Este CNPJ pertence ao Cadastro Padrão da empresa. Alterações '
            'cadastrais devem ser realizadas pelo Administrador Geral ou '
            'Administrador de Registro.'
        )


def is_outsourced_company_available_to_unit(connection, entity, unit_id):
    """True quando uma Empresa Terceirizada pode ser REFERENCIADA (não
    editada) por uma Unidade: empresa "do tenant" (``unit_id`` de origem
    nulo — sempre disponível, mesmo comportamento de antes da extensão de
    compartilhamento) OU já vinculada a essa Unidade especificamente.
    Usado só para leitura/uso (ex.: colaborador terceirizado apontando para
    a empresa) — edição/arquivamento do corporativo continua exigindo o
    vínculo explícito, ver ``ensure_actor_outsourced_company_scope``."""
    if entity.get('unit_id') is None:
        return True
    return bool(fetch_outsourced_company_unit_link(connection, entity['id'], unit_id))


# ── "Solicitar atualização cadastral" (ADR-0002 §12) ───────────────────────
# Quando o cadastro corporativo já foi promovido ao Cadastro Padrão,
# Administrador Local/Gestor de EPI perdem a edição direta
# (ensure_actor_can_edit_outsourced_company_corporate_fields acima) e
# passam a registrar aqui um pedido, para Administrador Geral/de Registro
# revisar — nunca uma edição automática. Modelo enxuto (pedido +
# resolução), não uma máquina de estados de várias etapas.

_UPDATE_REQUEST_SELECT_COLUMNS = (
    'id, company_id, outsourced_company_id, unit_id, requested_by_user_id, requested_by_name, '
    'message, status, resolved_by_user_id, resolved_at, resolution_notes, created_at, updated_at'
)

UPDATE_REQUEST_STATUSES: tuple[str, ...] = ('pending', 'resolved', 'dismissed')


def create_outsourced_company_update_request(connection, outsourced_company_id, company_id, unit_id, actor, message):
    message = str(message or '').strip()
    if not message:
        raise ValueError('Descreva o que precisa ser corrigido/atualizado.')
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO outsourced_company_update_requests (company_id, outsourced_company_id, unit_id, '
        "requested_by_user_id, requested_by_name, message, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
        (
            int(company_id), int(outsourced_company_id), int(unit_id) if unit_id else None,
            int(actor.get('id')) if actor and actor.get('id') else None,
            str((actor or {}).get('full_name') or '').strip(), message, now_iso, now_iso,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_outsourced_company_update_request_by_id(connection, request_id):
    row = connection.execute(
        f'SELECT {_UPDATE_REQUEST_SELECT_COLUMNS} FROM outsourced_company_update_requests '  # noqa: S608
        'WHERE id = ?',
        (int(request_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_outsourced_company_update_requests(connection, company_id, *, status=None):
    sql = (
        f'SELECT {_UPDATE_REQUEST_SELECT_COLUMNS} FROM outsourced_company_update_requests '  # noqa: S608
        'WHERE company_id = ?'
    )
    params = [int(company_id)]
    if status:
        sql += ' AND status = ?'
        params.append(status)
    rows = connection.execute(sql + ' ORDER BY created_at DESC', tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def resolve_outsourced_company_update_request(connection, request_id, company_id, actor_user_id, status, notes=''):
    normalized = status if status in ('resolved', 'dismissed') else 'resolved'
    now_iso = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE outsourced_company_update_requests SET status = ?, resolved_by_user_id = ?, '
        'resolved_at = ?, resolution_notes = ?, updated_at = ? WHERE id = ? AND company_id = ?',
        (
            normalized, int(actor_user_id) if actor_user_id else None, now_iso,
            str(notes or '').strip(), now_iso, int(request_id), int(company_id),
        ),
    )
    connection.commit()
    return normalized


def promote_outsourced_company(connection, entity_id, company_id):
    """Migração Simplificado → Padrão: mesma linha, mesmo id, sem duplicar
    nada. Exige CNPJ já preenchido (obrigatório no Padrão)."""
    current = get_outsourced_company_by_id(connection, entity_id)
    if not current or int(current['company_id']) != int(company_id):
        raise ValueError('Empresa terceirizada não encontrada nesta empresa.')
    if not current.get('cnpj'):
        raise ValueError('CNPJ é obrigatório para promover ao Cadastro Padrão.')
    now_iso = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE outsourced_companies SET registration_mode = 'standard', "
        "registration_status = 'complete', promoted_at = ?, updated_at = ? "
        'WHERE id = ? AND company_id = ?',
        (now_iso, now_iso, int(entity_id), int(company_id)),
    )
    connection.commit()


_PUBLIC_OUTSOURCED_COMPANY_FIELDS = (
    'id', 'legal_name', 'trade_name', 'cnpj', 'company_kind', 'registration_mode', 'registration_status',
)


def _mask_outsourced_company_public_fields(item):
    """Campos visíveis de uma empresa terceirizada AINDA NÃO vinculada à
    Unidade do ator (bloco "disponíveis para vinculação") — nunca notas,
    contratos, colaboradores ou a Unidade de origem, que são dado
    operacional de outra Unidade (ADR-0002 §12 item 12/13 do pedido)."""
    masked = {field: item.get(field) or '' for field in _PUBLIC_OUTSOURCED_COMPANY_FIELDS}
    masked['cnpj'] = mask_cnpj(item.get('cnpj'))
    return masked


def _linked_outsourced_company_ids(connection, unit_id):
    rows = connection.execute(
        'SELECT outsourced_company_id FROM outsourced_company_unit_links WHERE unit_id = ?',
        (int(unit_id),),
    ).fetchall()
    return {int(row_to_dict(row)['outsourced_company_id']) for row in rows}


def fetch_outsourced_companies(connection, company_id, *, actor=None):
    """Empresas terceirizadas do tenant, separadas por vínculo de Unidade
    (ADR-0002 §12 — compartilhamento por tenant): o cadastro corporativo é
    único por tenant, cada Unidade cria seu próprio vínculo via "Vincular à
    minha unidade" — a Unidade de origem não limita mais quem vê o quê.

    Devolve ``{'linked': [...], 'available': [...]}``:
    - ``linked``: dados completos das empresas "do tenant" (``unit_id`` de
      origem nulo, sempre disponíveis) + das já vinculadas à Unidade do
      ator. Para quem não é escopado por Unidade (general_admin/
      registry_admin/master_admin), são TODAS as empresas do tenant —
      mesmo comportamento de antes desta extensão.
    - ``available``: as demais — ainda sem vínculo com a Unidade do ator —
      só com os campos públicos (``_mask_outsourced_company_public_fields``).
      Sempre vazio para quem não é escopado por Unidade.
    """
    from core.archival import NON_OPERATIONAL_STATUSES, lifecycle_enabled
    sql = f'SELECT {_SELECT_COLUMNS} FROM outsourced_companies WHERE company_id = ?'  # noqa: S608
    params = [company_id]
    if lifecycle_enabled(connection, 'outsourced_companies'):
        placeholders = ', '.join(['?'] * len(NON_OPERATIONAL_STATUSES))
        sql += f' AND status NOT IN ({placeholders})'
        params.extend(NON_OPERATIONAL_STATUSES)
    rows = connection.execute(sql + ' ORDER BY legal_name', tuple(params)).fetchall()
    companies = [row_to_dict(row) for row in rows]

    if not actor or actor.get('role') not in ('admin', 'user'):
        return {'linked': companies, 'available': []}

    from core.repository import actor_operational_unit_id
    scope_unit_id = actor_operational_unit_id(connection, actor)
    return annotate_outsourced_company_visibility(connection, companies, scope_unit_id, split=True)


def annotate_outsourced_company_visibility(connection, companies, unit_id, *, split=False):
    """Aplica a mesma regra de ``fetch_outsourced_companies`` a uma lista
    arbitrária de empresas (ex.: resultado de busca do fluxo de vinculação)
    — nunca vazar dado operacional de uma empresa que a Unidade ainda não
    vinculou. Com ``split=True`` devolve ``{'linked': [...], 'available':
    [...]}``; com ``split=False`` (default) devolve uma lista só, com cada
    item completo (se disponível) ou mascarado (se não).

    Diferente de ``is_outsourced_company_available_to_unit`` (usada só para
    REFERENCIAR uma empresa "do tenant" a partir de qualquer Unidade — ex.:
    colaborador terceirizado), aqui ``unit_id`` de origem nulo NÃO basta
    para aparecer em ``linked``: precisa do vínculo explícito, para não
    listar como "gerenciável" algo que ``ensure_actor_outsourced_company_scope``
    bloquearia na hora de editar/arquivar (mesma trava, sem inconsistência
    entre o que a lista mostra e o que a escrita permite)."""
    linked_ids = _linked_outsourced_company_ids(connection, unit_id) if unit_id else set()
    linked, available = [], []
    for item in companies:
        if item['id'] in linked_ids:
            # `unit_id` truthy é garantido aqui — `linked_ids` só é não-vazio
            # quando `unit_id` foi informado (linha acima). O vínculo
            # também é garantido existir (é dele que `linked_ids` veio),
            # mas o `if link` defensivo evita um KeyError raro em caso de
            # corrida (vínculo desfeito entre a query de ids e esta).
            enriched = dict(item)
            link = fetch_outsourced_company_unit_link(connection, item['id'], unit_id)
            if link:
                enriched['local_status'] = link.get('local_status')
                enriched['unit_link_id'] = link.get('id')
            linked.append(enriched)
        else:
            available.append(_mask_outsourced_company_public_fields(item))
    if split:
        return {'linked': linked, 'available': available}
    return linked + available


def get_outsourced_company_by_id(connection, entity_id):
    row = connection.execute(
        f'SELECT {_SELECT_COLUMNS} FROM outsourced_companies WHERE id = ?',  # noqa: S608
        (entity_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


# ── Arquivamento (Soft Delete) — mesma política de Colaboradores/Unidades/EPIs
# (ADR-0002 §10.4). Reversível, preserva todo o histórico e a auditoria; sem
# fluxo de exclusão definitiva por ora (colaboradores vinculados via
# employees.outsourced_company_id não são apagados nem desvinculados — a
# empresa arquivada só fica bloqueada para NOVOS vínculos, via
# core.archival.ensure_record_operational, já usado em
# modules.employees.service.create_employee_outsourced_simplified).

def get_outsourced_company_lifecycle(connection, entity_id):
    """Empresa terceirizada com os campos de ciclo de vida (para arquivar/
    desarquivar) + ``registration_mode``, necessário para
    ``ensure_actor_can_edit_outsourced_company_corporate_fields`` decidir se
    a trava pós-promoção se aplica a este arquivamento."""
    from core.archival import LIFECYCLE_FIELD_NAMES, lifecycle_enabled
    extra = (', ' + ', '.join(LIFECYCLE_FIELD_NAMES)) if lifecycle_enabled(connection, 'outsourced_companies') else ''
    row = connection.execute(
        f'SELECT id, company_id, unit_id, legal_name, trade_name, registration_mode{extra} '  # noqa: S608
        'FROM outsourced_companies WHERE id = ?',
        (int(entity_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_archived_outsourced_companies(connection, actor):
    """Empresas terceirizadas arquivadas do tenant, com dados de retenção (para a UI)."""
    from core.archival import STATUS_ARCHIVED, STATUS_PENDING_DELETION, retention_days_remaining
    sql = (
        'SELECT outsourced_companies.id, outsourced_companies.company_id, '
        'outsourced_companies.unit_id, '
        'outsourced_companies.legal_name, outsourced_companies.trade_name, '
        'outsourced_companies.cnpj, outsourced_companies.company_kind, '
        'outsourced_companies.status, outsourced_companies.archived_at, '
        'outsourced_companies.archived_by, outsourced_companies.archive_reason, '
        'outsourced_companies.retention_until, outsourced_companies.legal_hold, '
        'users.full_name AS archived_by_name '
        'FROM outsourced_companies '
        'LEFT JOIN users ON users.id = outsourced_companies.archived_by '
        'WHERE outsourced_companies.status IN (?, ?)'
    )
    params = [STATUS_ARCHIVED, STATUS_PENDING_DELETION]
    if actor and actor.get('role') != 'master_admin':
        sql += ' AND outsourced_companies.company_id = ?'
        params.append(actor['company_id'])
    # Mesmo escopo de ensure_actor_outsourced_company_scope: só as empresas
    # "do tenant" (unit_id de origem nulo) ou já vinculadas à Unidade do ator
    # (outsourced_company_unit_links) — não mais "unit_id de origem == minha
    # Unidade" (ADR-0002 §12, compartilhamento por tenant).
    if actor and actor.get('role') in ('admin', 'user'):
        from core.repository import actor_operational_unit_id
        scope_unit_id = actor_operational_unit_id(connection, actor)
        sql += (
            ' AND (outsourced_companies.unit_id IS NULL OR outsourced_companies.id IN '
            '(SELECT outsourced_company_id FROM outsourced_company_unit_links WHERE unit_id = ?))'
        )
        params.append(scope_unit_id or 0)
    rows = connection.execute(
        sql + ' ORDER BY outsourced_companies.archived_at DESC', tuple(params),
    ).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['retention_days_remaining'] = retention_days_remaining(item.get('retention_until'))
        result.append(item)
    return result


# ── Vínculo do colaborador (Cadastro Simplificado, ADR-014 PR 3) ──────────

def validate_employee_outsourced_reference(connection, payload, company_id, *, unit_id=None):
    """Valida os campos opcionais que ligam um colaborador (``employees``) a
    uma empresa terceirizada/prestadora e, opcionalmente, a um contrato.

    Chamado por ``modules.employees.service.create_employee``/
    ``update_employee`` — nunca cria nem edita a empresa terceirizada em si,
    só valida a referência. Ausência de ``outsourced_company_id`` (CLT) é o
    caso comum e retorna tudo vazio/``None``, preservando compatibilidade.

    Regras: ``outsourced_company_id`` e ``service_contract_id`` (quando
    informados) precisam pertencer ao mesmo tenant do colaborador — nunca a
    outro; um contrato informado precisa pertencer à empresa terceirizada
    informada, quando as duas vêm juntas; exceção individual de
    responsabilidade pelo EPI exige motivo. Quando ``unit_id`` é informado
    (Unidade-alvo do colaborador), a empresa terceirizada precisa estar
    DISPONÍVEL para essa Unidade — "do tenant" (sem Unidade de origem) ou
    já vinculada a ela via ``outsourced_company_unit_links`` (ADR-0002 §12,
    compartilhamento por tenant) — nunca referenciar uma empresa que a
    Unidade do colaborador não vinculou.
    """
    payload = payload or {}
    outsourced_company_id = payload.get('outsourced_company_id')
    if outsourced_company_id in (None, '', 0, '0'):
        outsourced_company_id = None
    else:
        outsourced_company_id = int(outsourced_company_id)
        company_row = get_outsourced_company_by_id(connection, outsourced_company_id)
        if not company_row or int(company_row['company_id']) != int(company_id):
            raise ValueError('Empresa terceirizada não encontrada nesta empresa.')
        if unit_id is not None and not is_outsourced_company_available_to_unit(connection, company_row, unit_id):
            raise ValueError(
                'Empresa terceirizada não está vinculada à Unidade do colaborador — '
                'vincule a empresa à Unidade antes de cadastrar o colaborador.'
            )

    service_contract_id = payload.get('service_contract_id')
    if service_contract_id in (None, '', 0, '0'):
        service_contract_id = None
    else:
        service_contract_id = int(service_contract_id)
        contract_row = connection.execute(
            'SELECT id, company_id, outsourced_company_id FROM service_contracts WHERE id = ?',
            (service_contract_id,),
        ).fetchone()
        contract = row_to_dict(contract_row) if contract_row else None
        if not contract or int(contract['company_id']) != int(company_id):
            raise ValueError('Contrato não encontrado nesta empresa.')
        if outsourced_company_id and int(contract['outsourced_company_id']) != int(outsourced_company_id):
            raise ValueError('Contrato não pertence à empresa terceirizada informada.')

    override = str(payload.get('epi_responsibility_override') or '').strip()
    override_reason = str(payload.get('epi_responsibility_override_reason') or '').strip()
    if override:
        override = normalize_epi_responsibility(override)
        if not override_reason:
            raise ValueError('Motivo é obrigatório ao sobrescrever a responsabilidade pelo EPI do colaborador.')
    else:
        override = ''
        override_reason = ''

    return outsourced_company_id, service_contract_id, override, override_reason


# ── Contratos ─────────────────────────────────────────────────────────────

def validate_service_contract_payload(connection, payload, company_id, outsourced_company_id):
    payload = payload or {}
    company_row = get_outsourced_company_by_id(connection, outsourced_company_id)
    if not company_row or int(company_row['company_id']) != int(company_id):
        raise ValueError('Empresa terceirizada não encontrada nesta empresa.')

    unit_id = payload.get('unit_id')
    if unit_id in (None, '', 0, '0'):
        unit_id = None
    else:
        unit_id = int(unit_id)
        unit = connection.execute(
            'SELECT id FROM units WHERE id = ? AND company_id = ? LIMIT 1', (unit_id, company_id),
        ).fetchone()
        if not unit:
            raise ValueError('Unidade não encontrada nesta empresa.')

    override = str(payload.get('epi_responsibility_override') or '').strip()
    if override:
        override = normalize_epi_responsibility(override)
        if not str(payload.get('override_reason') or '').strip():
            raise ValueError('Motivo é obrigatório ao sobrescrever a responsabilidade pelo EPI do contrato.')

    return {
        'company_id': int(company_id),
        'outsourced_company_id': int(outsourced_company_id),
        'unit_id': unit_id,
        'contract_ref': str(payload.get('contract_ref') or '').strip(),
        'service_order_ref': str(payload.get('service_order_ref') or '').strip(),
        'start_date': str(payload.get('start_date') or '').strip(),
        'end_date': str(payload.get('end_date') or '').strip(),
        'epi_responsibility_override': override,
        'override_reason': str(payload.get('override_reason') or '').strip() if override else '',
        'status': str(payload.get('status') or 'Ativo').strip() or 'Ativo',
    }


def create_service_contract(connection, payload, company_id, outsourced_company_id, actor_user_id=None):
    validated = validate_service_contract_payload(connection, payload, company_id, outsourced_company_id)
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO service_contracts (company_id, outsourced_company_id, unit_id, contract_ref, '
        'service_order_ref, start_date, end_date, epi_responsibility_override, override_reason, status, '
        'created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            validated['company_id'], validated['outsourced_company_id'], validated['unit_id'],
            validated['contract_ref'], validated['service_order_ref'], validated['start_date'], validated['end_date'],
            validated['epi_responsibility_override'], validated['override_reason'],
            validated['status'], int(actor_user_id) if actor_user_id else None, now_iso, now_iso,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def fetch_service_contracts(connection, company_id, outsourced_company_id):
    rows = connection.execute(
        f'SELECT {_CONTRACT_SELECT_COLUMNS} FROM service_contracts '  # noqa: S608
        'WHERE company_id = ? AND outsourced_company_id = ? ORDER BY created_at DESC',
        (company_id, outsourced_company_id),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def resolve_effective_epi_responsibility(connection, *, outsourced_company_id=None, service_contract_id=None,
                                          employee_override=None):
    """Resolve a responsabilidade efetiva pelo fornecimento de EPI, na ordem
    de precedência: exceção individual do colaborador > exceção do contrato
    > default da empresa terceirizada > 'Não Definido' (CLT sem empresa
    terceirizada não passa por aqui — chamador decide o default nesse caso).
    """
    if str(employee_override or '').strip():
        return normalize_epi_responsibility(employee_override)

    if service_contract_id:
        contract = connection.execute(
            'SELECT epi_responsibility_override FROM service_contracts WHERE id = ?',
            (int(service_contract_id),),
        ).fetchone()
        if contract:
            override = row_to_dict(contract).get('epi_responsibility_override')
            if str(override or '').strip():
                return normalize_epi_responsibility(override)

    if outsourced_company_id:
        company_row = get_outsourced_company_by_id(connection, outsourced_company_id)
        if company_row:
            return normalize_epi_responsibility(company_row.get('epi_responsibility'))

    return 'Não Definido'


# ── Snapshot histórico na entrega (ADR-0002, PR 4) ─────────────────────────

def resolve_delivery_outsourced_snapshot(connection, employee, company_id):
    """Congela, para uma entrega sendo criada agora, os atributos do vínculo
    do colaborador com empresa terceirizada/prestadora no momento exato da
    entrega — para nunca mudar depois, mesmo que a empresa/contrato seja
    editado ou o colaborador seja migrado para outra terceirizada.

    ``employee`` é o dict já carregado pelo chamador (mesma linha que
    ``core.repository.get_employee_by_id`` devolve) — não faz query extra
    para os campos que já estão nele. Retorna um dict pronto para
    desempacotar nas colunas ``snapshot_*`` de ``deliveries``.

    Colaborador CLT (sem ``outsourced_company_id``): todo o snapshot fica
    vazio, exceto ``tipo_vinculo`` (sempre conhecido, ex. ``'CLT'``) — não
    há empresa terceirizada nem responsabilidade pelo EPI para congelar.
    """
    employee = employee or {}
    outsourced_company_id = employee.get('outsourced_company_id')
    service_contract_id = employee.get('service_contract_id')
    snapshot = {
        'snapshot_tipo_vinculo': str(employee.get('tipo_vinculo') or 'CLT').strip() or 'CLT',
        'snapshot_outsourced_company_name': '',
        'snapshot_outsourced_company_cnpj': '',
        'snapshot_contracting_company_id': int(company_id) if company_id else None,
        'snapshot_contract_ref': '',
        'snapshot_epi_responsibility': '',
    }
    if not outsourced_company_id:
        return snapshot

    company_row = get_outsourced_company_by_id(connection, outsourced_company_id)
    if company_row:
        snapshot['snapshot_outsourced_company_name'] = company_row.get('legal_name') or ''
        snapshot['snapshot_outsourced_company_cnpj'] = company_row.get('cnpj') or ''

    if service_contract_id:
        contract_row = connection.execute(
            'SELECT contract_ref FROM service_contracts WHERE id = ?', (int(service_contract_id),),
        ).fetchone()
        if contract_row:
            snapshot['snapshot_contract_ref'] = row_to_dict(contract_row).get('contract_ref') or ''

    snapshot['snapshot_epi_responsibility'] = resolve_effective_epi_responsibility(
        connection,
        outsourced_company_id=outsourced_company_id,
        service_contract_id=service_contract_id,
        employee_override=employee.get('epi_responsibility_override'),
    )
    return snapshot


# ── Ressarcimento (ADR-0002, PR 6) ─────────────────────────────────────────
#
# Registro de apoio para conferência manual — NUNCA cobrança automática.
# Uma linha liga uma entrega já realizada a uma empresa terceirizada quando
# a responsabilidade efetiva pelo EPI diverge de quem operou a entrega.
# Relatórios de ressarcimento são consultas sobre esta tabela; nenhuma
# integração de pagamento/fatura é disparada por mudança de status.

_REIMBURSEMENT_SELECT_COLUMNS = (
    'id, company_id, delivery_id, outsourced_company_id, unit_cost, quantity, total_value, '
    'reason, contract_ref, status, created_by_user_id, created_at, updated_at'
)


def normalize_reimbursement_status(value) -> str:
    value = str(value or '').strip()
    return value if value in REIMBURSEMENT_STATUSES else 'Não Aplicável'


def validate_reimbursement_payload(connection, payload, company_id):
    payload = payload or {}
    delivery_id = payload.get('delivery_id')
    if delivery_id in (None, '', 0, '0'):
        raise ValueError('delivery_id é obrigatório.')
    delivery_id = int(delivery_id)
    delivery_row = connection.execute(
        'SELECT id, company_id FROM deliveries WHERE id = ?', (delivery_id,),
    ).fetchone()
    delivery = row_to_dict(delivery_row) if delivery_row else None
    if not delivery or int(delivery['company_id']) != int(company_id):
        raise ValueError('Entrega não encontrada nesta empresa.')

    outsourced_company_id = payload.get('outsourced_company_id')
    if outsourced_company_id in (None, '', 0, '0'):
        raise ValueError('outsourced_company_id é obrigatório.')
    outsourced_company_id = int(outsourced_company_id)
    company_row = get_outsourced_company_by_id(connection, outsourced_company_id)
    if not company_row or int(company_row['company_id']) != int(company_id):
        raise ValueError('Empresa terceirizada não encontrada nesta empresa.')

    quantity = int(payload.get('quantity') or 1)
    unit_cost = float(payload.get('unit_cost') or 0)
    total_value = payload.get('total_value')
    total_value = float(total_value) if total_value not in (None, '') else round(unit_cost * quantity, 2)

    return {
        'company_id': int(company_id),
        'delivery_id': delivery_id,
        'outsourced_company_id': outsourced_company_id,
        'unit_cost': unit_cost,
        'quantity': quantity,
        'total_value': total_value,
        'reason': str(payload.get('reason') or '').strip(),
        'contract_ref': str(payload.get('contract_ref') or '').strip(),
        'status': normalize_reimbursement_status(payload.get('status') or 'Pendente de Análise'),
    }


def create_reimbursement(connection, payload, company_id, actor_user_id=None):
    validated = validate_reimbursement_payload(connection, payload, company_id)
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO epi_reimbursements (company_id, delivery_id, outsourced_company_id, unit_cost, '
        'quantity, total_value, reason, contract_ref, status, created_by_user_id, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            validated['company_id'], validated['delivery_id'], validated['outsourced_company_id'],
            validated['unit_cost'], validated['quantity'], validated['total_value'],
            validated['reason'], validated['contract_ref'], validated['status'],
            int(actor_user_id) if actor_user_id else None, now_iso, now_iso,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_reimbursement_status(connection, reimbursement_id, company_id, status):
    normalized = normalize_reimbursement_status(status)
    now_iso = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE epi_reimbursements SET status = ?, updated_at = ? WHERE id = ? AND company_id = ?',
        (normalized, now_iso, int(reimbursement_id), int(company_id)),
    )
    connection.commit()
    return normalized


def get_reimbursement_by_id(connection, reimbursement_id):
    row = connection.execute(
        f'SELECT {_REIMBURSEMENT_SELECT_COLUMNS} FROM epi_reimbursements WHERE id = ?',  # noqa: S608
        (int(reimbursement_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_reimbursements(connection, company_id, *, outsourced_company_id=None, status=None):
    sql = f'SELECT {_REIMBURSEMENT_SELECT_COLUMNS} FROM epi_reimbursements WHERE company_id = ?'  # noqa: S608
    params = [int(company_id)]
    if outsourced_company_id:
        sql += ' AND outsourced_company_id = ?'
        params.append(int(outsourced_company_id))
    if status:
        sql += ' AND status = ?'
        params.append(normalize_reimbursement_status(status))
    sql += ' ORDER BY created_at DESC'
    rows = connection.execute(sql, tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


# ── Alerta de sugestão de migração Simplificado → Padrão (PR 6) ───────────

DEFAULT_SIMPLIFIED_DURATION_THRESHOLD_DAYS = 30
_SIMPLIFIED_THRESHOLD_CONFIG_KEY = 'outsourced_simplified_duration_threshold_days'


def get_simplified_duration_threshold_days(connection, company_id) -> int:
    """Limiar (em dias) para sugerir a migração Simplificado → Padrão —
    configurável por tenant via ``configuration_framework`` (mesmo storage
    do ``module_visibility``), nunca hardcoded no fluxo. Cai para o default
    de sistema quando o tenant não configurou nada, ou quando o próprio
    framework de configuração ainda não está provisionado (retrocompatível).
    """
    try:
        from modules.settings.service import get_configuration_framework
        framework = get_configuration_framework(connection, company_id)
        raw = (framework or {}).get(_SIMPLIFIED_THRESHOLD_CONFIG_KEY)
        return int(raw) if raw not in (None, '') else DEFAULT_SIMPLIFIED_DURATION_THRESHOLD_DAYS
    except Exception:
        return DEFAULT_SIMPLIFIED_DURATION_THRESHOLD_DAYS


def fetch_migration_suggestions(connection, company_id):
    """Empresas terceirizadas ainda em Cadastro Simplificado há mais tempo
    que o limiar configurado — sugestão de promoção ao Cadastro Padrão,
    nunca bloqueio. O colaborador e a operação seguem funcionando
    normalmente independente desta lista; é só um lembrete para quem
    administra o cadastro.
    """
    threshold_days = get_simplified_duration_threshold_days(connection, company_id)
    rows = connection.execute(
        f'SELECT {_SELECT_COLUMNS} FROM outsourced_companies '  # noqa: S608
        "WHERE company_id = ? AND registration_mode = 'simplified' "
        "AND registration_status != 'archived' "
        "ORDER BY created_at",
        (int(company_id),),
    ).fetchall()
    companies = [row_to_dict(row) for row in rows]
    now = datetime.now(UTC)
    suggestions = []
    for company in companies:
        created_at = str(company.get('created_at') or '').strip()
        if not created_at:
            continue
        try:
            created = datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
        except ValueError:
            continue
        age_days = (now - created).days
        if age_days >= threshold_days:
            suggestions.append({
                'outsourced_company_id': company['id'],
                'legal_name': company['legal_name'],
                'registration_mode': company['registration_mode'],
                'age_days': age_days,
                'threshold_days': threshold_days,
            })
    return suggestions


# ── Relatórios (ADR-0002 §10) ───────────────────────────────────────────────
# Complementa os relatórios de entrega (modules.reports.service, já com
# dimensões de empresa terceirizada desde o PR6) com um resumo de
# colaboradores por empresa terceirizada/prestadora — headcount ativo vs.
# arquivado e distribuição por tipo de vínculo, para a aba "Relatórios" do
# Cadastro de Colaboradores.

def fetch_outsourced_employees_summary(connection, company_id, *, actor=None):
    """Resumo de colaboradores (ativos + arquivados) por empresa terceirizada
    do tenant: total, contagem ativa/arquivada e distribuição por
    tipo_vinculo. Empresas sem nenhum colaborador vinculado aparecem com
    contagens zeradas (não somem do relatório). Administrador Local/Gestor
    de EPI só veem: as Empresas Terceirizadas disponíveis para a própria
    Unidade (mesmo escopo de fetch_outsourced_companies/
    ensure_actor_outsourced_company_scope — ADR-0002 §12) e, dentro delas,
    só os PRÓPRIOS colaboradores (``employees.unit_id`` == Unidade do ator)
    — nunca o headcount de outra Unidade que também vinculou a mesma
    empresa compartilhada (não vazar dado operacional de outra Unidade)."""
    from epi_backend.db import table_columns
    if 'outsourced_company_id' not in table_columns(connection, 'employees'):
        return []
    lifecycle = 'status' in table_columns(connection, 'employees')
    status_col = 'employees.status' if lifecycle else "'active'"
    join_clause = 'LEFT JOIN employees ON employees.outsourced_company_id = outsourced_companies.id '
    params = [int(company_id)]
    scope_unit_id = None
    if actor and actor.get('role') in ('admin', 'user'):
        from core.repository import actor_operational_unit_id
        scope_unit_id = actor_operational_unit_id(connection, actor) or 0
        join_clause += 'AND employees.unit_id = ? '
    sql = (
        f'SELECT outsourced_companies.id AS outsourced_company_id, '  # noqa: S608
        'outsourced_companies.legal_name, outsourced_companies.trade_name, '
        'employees.id AS employee_id, employees.tipo_vinculo, '
        f'{status_col} AS employee_status '
        'FROM outsourced_companies '
        f'{join_clause}'
        'WHERE outsourced_companies.company_id = ? '
    )
    if scope_unit_id is not None:
        params = [scope_unit_id, int(company_id)]
        sql += (
            ' AND (outsourced_companies.unit_id IS NULL OR outsourced_companies.id IN '
            '(SELECT outsourced_company_id FROM outsourced_company_unit_links WHERE unit_id = ?))'
        )
        params.append(scope_unit_id)
    rows = connection.execute(
        sql + 'ORDER BY outsourced_companies.legal_name', tuple(params),
    ).fetchall()
    summary = {}
    order = []
    for row in rows:
        item = row_to_dict(row)
        oc_id = item['outsourced_company_id']
        if oc_id not in summary:
            summary[oc_id] = {
                'outsourced_company_id': oc_id,
                'legal_name': item['legal_name'],
                'trade_name': item['trade_name'],
                'active_count': 0,
                'archived_count': 0,
                'by_tipo_vinculo': {},
            }
            order.append(oc_id)
        if item.get('employee_id') is None:
            continue
        entry = summary[oc_id]
        status = str(item.get('employee_status') or 'active')
        if status in ('archived', 'pending_deletion', 'deleted'):
            entry['archived_count'] += 1
        else:
            entry['active_count'] += 1
        tipo = str(item.get('tipo_vinculo') or 'Não informado')
        entry['by_tipo_vinculo'][tipo] = entry['by_tipo_vinculo'].get(tipo, 0) + 1
    return [summary[oc_id] for oc_id in order]
