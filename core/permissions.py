"""Constantes e mapa de permissões do sistema EPI Controle."""

# --- Permissões individuais ---

PERM_DASHBOARD_VIEW = 'dashboard:view'

PERM_USERS_VIEW = 'users:view'
PERM_USERS_CREATE = 'users:create'
PERM_USERS_UPDATE = 'users:update'
PERM_USERS_DELETE = 'users:delete'

PERM_UNITS_VIEW = 'units:view'
PERM_UNITS_CREATE = 'units:create'
PERM_UNITS_UPDATE = 'units:update'
PERM_UNITS_DELETE = 'units:delete'

PERM_EMPLOYEES_VIEW = 'employees:view'
PERM_EMPLOYEES_CREATE = 'employees:create'
PERM_EMPLOYEES_UPDATE = 'employees:update'
PERM_EMPLOYEES_DELETE = 'employees:delete'
# Mudança do vínculo jurídico (CNPJ) do colaborador. O CNPJ é imutável na
# edição comum; esta permissão libera o processo administrativo auditado.
PERM_EMPLOYEES_LEGAL_ENTITY_TRANSFER = 'employees:legal_entity_transfer'
# Movimentação entre unidades (temporária ou definitiva). Distinta de
# PERM_EMPLOYEES_UPDATE (edição de dados cadastrais): o Administrador Local
# transfere colaboradores entre as unidades da sua carteira, mas não edita
# cadastro nem reativa desligados — atribuição do Administrador de Registro
# (docs/PAPEIS_E_ATRIBUICOES.md #3 vs #4).
PERM_EMPLOYEES_TRANSFER = 'employees:transfer'
# Cadastro/edição simplificado de colaborador terceirizado/prestador
# (ADR-0002 §10.2), restrito à aba "Cadastro de Colaboradores" do módulo
# terceirizados_colaboradores — nunca ao cadastro completo de CLT.
# Intencionalmente distinta de PERM_EMPLOYEES_CREATE/UPDATE: Administrador
# Local e Gestor de EPI não ganham o cadastro completo por causa disto.
PERM_EMPLOYEES_CREATE_SIMPLIFIED = 'employees:create_simplified'
PERM_EMPLOYEES_UPDATE_SIMPLIFIED = 'employees:update_simplified'

PERM_EPIS_VIEW = 'epis:view'
PERM_EPIS_CREATE = 'epis:create'
PERM_EPIS_UPDATE = 'epis:update'
PERM_EPIS_DELETE = 'epis:delete'

PERM_DELIVERIES_VIEW = 'deliveries:view'
PERM_DELIVERIES_CREATE = 'deliveries:create'

PERM_FICHAS_VIEW = 'fichas:view'
PERM_REPORTS_VIEW = 'reports:view'
PERM_ALERTS_VIEW = 'alerts:view'

PERM_COMPANIES_VIEW = 'companies:view'
PERM_COMPANIES_CREATE = 'companies:create'
PERM_COMPANIES_UPDATE = 'companies:update'
PERM_COMPANIES_LICENSE = 'companies:license'
# Suporte excepcional do Administrador Master a dados da empresa (auditado)
PERM_COMPANIES_SUPPORT = 'companies:support'

# Pessoas jurídicas (CNPJs) vinculadas à empresa contratante — arquitetura
# Multi-CNPJ / Joint Venture. Cada empresa (tenant) pode ter uma ou várias
# LegalEntity (matriz, filiais, subsidiárias, SPEs, sócias de JV).
PERM_LEGAL_ENTITIES_VIEW = 'legal_entities:view'
PERM_LEGAL_ENTITIES_CREATE = 'legal_entities:create'
PERM_LEGAL_ENTITIES_UPDATE = 'legal_entities:update'
PERM_LEGAL_ENTITIES_DELETE = 'legal_entities:delete'

# Configuração da própria empresa (Configurações > Minha Empresa) — Owner da tenant
PERM_COMPANY_SETTINGS_VIEW = 'company_settings:view'
PERM_COMPANY_SETTINGS_UPDATE = 'company_settings:update'

PERM_COMMERCIAL_VIEW = 'commercial:view'
PERM_USAGE_VIEW = 'usage:view'

PERM_STOCK_VIEW = 'stock:view'
PERM_STOCK_ADJUST = 'stock:adjust'

PERM_SETTINGS_VIEW = 'settings:view'
PERM_SETTINGS_UPDATE = 'settings:update'

PERM_EPI_VIEW_SELF = 'epi:view_self'
PERM_EPI_SIGN = 'epi:sign'

PERM_PURCHASE_REQUESTS_VIEW = 'purchase_requests:view'
PERM_PURCHASE_REQUESTS_CREATE = 'purchase_requests:create'
PERM_PURCHASE_REQUESTS_UPDATE = 'purchase_requests:update'

PERM_PO_VIEW = 'purchase_orders:view'
PERM_PO_CREATE = 'purchase_orders:create'
PERM_PO_UPLOAD = 'purchase_orders:upload'
PERM_PO_APPROVE = 'purchase_orders:approve'
PERM_PO_RECEIVE = 'purchase_orders:receive'
PERM_PO_REVIEW = 'purchase_orders:review'

PERM_FINANCE_VIEW = 'finance:view'
PERM_SUPPLIERS_MANAGE = 'suppliers:manage'
PERM_UNIT_LINKS_MANAGE = 'unit_links:manage'

# Módulo de Compras — cotações (RFQ) e catálogo de fornecedores (Fase F0)
PERM_QUOTES_VIEW = 'quotes:view'
PERM_QUOTES_MANAGE = 'quotes:manage'
PERM_SUPPLIER_CATALOG_VIEW = 'supplier_catalog:view'

PERM_EPI_FEEDBACK_VIEW = 'epi_feedback:view'
PERM_EPI_FEEDBACK_CREATE = 'epi_feedback:create'
PERM_EPI_FEEDBACK_TRIAGE = 'epi_feedback:triage'
PERM_EPI_FEEDBACK_HSEQ_REVIEW = 'epi_feedback:hseq_review'
PERM_EPI_FEEDBACK_ADMIN_APPROVE = 'epi_feedback:admin_approve'
PERM_EPI_FEEDBACK_CLOSE = 'epi_feedback:close'
PERM_EPI_FEEDBACK_MANAGER_EVAL = 'epi_feedback:manager_eval'

PERM_EPI_EVALUATION_VIEW = 'epi_evaluation:view'
PERM_EPI_EVALUATION_DECIDE = 'epi_evaluation:decide'
PERM_EPI_SUGGESTION_ACCEPT = 'epi_evaluation:accept_suggestion'

# --- Fluxo de EPI em teste (novo EPI ainda não homologado) ---
PERM_PPE_TEST_VIEW = 'ppe_test:view'
PERM_PPE_TEST_SUGGEST = 'ppe_test:suggest'
PERM_PPE_TEST_TRIAGE = 'ppe_test:triage'
PERM_PPE_TEST_MANAGE = 'ppe_test:manage'
PERM_PPE_TEST_EVALUATE = 'ppe_test:evaluate'
PERM_PPE_TEST_TECH_REVIEW = 'ppe_test:tech_review'
PERM_PPE_TEST_DECIDE = 'ppe_test:decide'
PERM_PPE_TEST_HOMOLOGATE = 'ppe_test:homologate'

# --- Grupos de permissões reutilizáveis ---

ADMIN_BASE_PERMISSIONS: frozenset[str] = frozenset({
    PERM_DASHBOARD_VIEW,
    PERM_USERS_VIEW, PERM_USERS_CREATE, PERM_USERS_UPDATE, PERM_USERS_DELETE,
    PERM_UNITS_VIEW, PERM_UNITS_CREATE, PERM_UNITS_UPDATE, PERM_UNITS_DELETE,
    PERM_EMPLOYEES_VIEW, PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_DELETE,
    PERM_EMPLOYEES_TRANSFER,
    # Superset de PERM_EMPLOYEES_CREATE/UPDATE — quem já tem o cadastro
    # completo também usa o formulário simplificado sem exceção de rota.
    PERM_EMPLOYEES_CREATE_SIMPLIFIED, PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
    PERM_EPIS_VIEW, PERM_EPIS_CREATE, PERM_EPIS_UPDATE, PERM_EPIS_DELETE,
    PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_REPORTS_VIEW, PERM_ALERTS_VIEW, PERM_STOCK_VIEW,
    PERM_LEGAL_ENTITIES_VIEW,
})

DELIVERY_WRITE_PERMISSIONS: frozenset[str] = frozenset({PERM_DELIVERIES_CREATE})
COMPANY_CORE_PERMISSIONS: frozenset[str] = frozenset({PERM_COMPANIES_VIEW})
COMPANY_MANAGEMENT_PERMISSIONS: frozenset[str] = frozenset({
    PERM_COMPANIES_CREATE, PERM_COMPANIES_UPDATE, PERM_COMPANIES_LICENSE,
})
# Gestão de CNPJs (LegalEntity) da própria empresa — Administrador Geral e
# Administrador de Registro. O Administrador Master gerencia via suporte.
LEGAL_ENTITY_MANAGEMENT_PERMISSIONS: frozenset[str] = frozenset({
    PERM_LEGAL_ENTITIES_CREATE, PERM_LEGAL_ENTITIES_UPDATE, PERM_LEGAL_ENTITIES_DELETE,
    # Processo administrativo de mudança do vínculo jurídico do colaborador.
    PERM_EMPLOYEES_LEGAL_ENTITY_TRANSFER,
})
COMMERCIAL_PERMISSIONS: frozenset[str] = frozenset({PERM_COMMERCIAL_VIEW, PERM_USAGE_VIEW})
STOCK_MANAGEMENT_PERMISSIONS: frozenset[str] = frozenset({PERM_STOCK_ADJUST})

PURCHASE_VIEW_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PURCHASE_REQUESTS_VIEW, PERM_PO_VIEW, PERM_FINANCE_VIEW,
    PERM_QUOTES_VIEW, PERM_SUPPLIER_CATALOG_VIEW,
})
PURCHASE_BUYER_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PURCHASE_REQUESTS_VIEW, PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PO_VIEW, PERM_PO_CREATE, PERM_PO_UPLOAD, PERM_FINANCE_VIEW,
    PERM_QUOTES_VIEW, PERM_QUOTES_MANAGE, PERM_SUPPLIER_CATALOG_VIEW,
})
PURCHASE_APPROVER_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PURCHASE_REQUESTS_VIEW, PERM_PO_VIEW, PERM_PO_APPROVE, PERM_FINANCE_VIEW,
    PERM_QUOTES_VIEW, PERM_SUPPLIER_CATALOG_VIEW,
})
PURCHASE_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PURCHASE_REQUESTS_VIEW, PERM_PURCHASE_REQUESTS_CREATE, PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PO_VIEW, PERM_PO_REVIEW, PERM_PO_RECEIVE, PERM_FINANCE_VIEW,
    PERM_QUOTES_VIEW, PERM_SUPPLIER_CATALOG_VIEW,
})

# Administrador Master não deve reter permissão permanente de execução
# operacional (docs/PAPEIS_E_ATRIBUICOES.md #1: "Não faz"). O acesso a estas
# ações, quando necessário para suporte, deve passar por um mecanismo
# formal de impersonation/acesso temporário auditado — ainda não
# implementado — e nunca por concessão permanente no papel.
MASTER_ADMIN_OPERATIONAL_EXCLUSIONS: frozenset[str] = frozenset({
    PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_DELETE,
    PERM_EMPLOYEES_CREATE_SIMPLIFIED, PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
    PERM_DELIVERIES_CREATE, PERM_STOCK_ADJUST,
    PERM_PURCHASE_REQUESTS_CREATE, PERM_PURCHASE_REQUESTS_UPDATE,
})

EPI_FEEDBACK_MANAGER_PERMISSIONS: frozenset[str] = frozenset({
    PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_TRIAGE,
})

# Fluxo de EPI em teste — grupos por papel funcional.
# Gestor de EPI (role 'user' — 'epi_manager' é apenas um apelido histórico do
# mesmo papel, normalizado por ROLE_ALIASES em core/roles.py) opera o teste na
# unidade, faz a triagem e a análise técnica, mas não decide nem homologa.
# Administrador Geral e Administrador de Registro decidem, definem escopo e
# homologam. Administrador Master atua somente em suporte auditado (view).
PPE_TEST_LOCAL_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PPE_TEST_VIEW, PERM_PPE_TEST_SUGGEST, PERM_PPE_TEST_MANAGE, PERM_PPE_TEST_EVALUATE,
    PERM_PPE_TEST_TRIAGE, PERM_PPE_TEST_TECH_REVIEW,
})
PPE_TEST_GENERAL_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PPE_TEST_VIEW, PERM_PPE_TEST_SUGGEST, PERM_PPE_TEST_TRIAGE, PERM_PPE_TEST_MANAGE,
    PERM_PPE_TEST_EVALUATE, PERM_PPE_TEST_TECH_REVIEW, PERM_PPE_TEST_DECIDE, PERM_PPE_TEST_HOMOLOGATE,
})
PPE_TEST_REGISTRY_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    PERM_PPE_TEST_VIEW, PERM_PPE_TEST_SUGGEST, PERM_PPE_TEST_TRIAGE, PERM_PPE_TEST_MANAGE,
    PERM_PPE_TEST_EVALUATE, PERM_PPE_TEST_TECH_REVIEW,
})
EPI_FEEDBACK_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_ADMIN_APPROVE, PERM_EPI_FEEDBACK_CLOSE,
})

# --- Mapa final de permissões por role ---

PERMISSIONS: dict[str, frozenset[str]] = {
    'master_admin': (
        ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS
        | COMPANY_MANAGEMENT_PERMISSIONS | LEGAL_ENTITY_MANAGEMENT_PERMISSIONS
        | COMMERCIAL_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS
        | PURCHASE_VIEW_PERMISSIONS | PURCHASE_BUYER_PERMISSIONS | PURCHASE_APPROVER_PERMISSIONS
        | PURCHASE_ADMIN_PERMISSIONS | EPI_FEEDBACK_MANAGER_PERMISSIONS | EPI_FEEDBACK_ADMIN_PERMISSIONS
        | frozenset({
            PERM_PURCHASE_REQUESTS_CREATE, PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE,
            PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE,
            PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE,
            PERM_COMPANIES_SUPPORT,
            PERM_PPE_TEST_VIEW,
        })
    ) - MASTER_ADMIN_OPERATIONAL_EXCLUSIONS,
    'general_admin': (
        ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS
        | LEGAL_ENTITY_MANAGEMENT_PERMISSIONS
        | STOCK_MANAGEMENT_PERMISSIONS | PURCHASE_VIEW_PERMISSIONS | PURCHASE_BUYER_PERMISSIONS
        | PURCHASE_APPROVER_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS
        | EPI_FEEDBACK_MANAGER_PERMISSIONS | EPI_FEEDBACK_ADMIN_PERMISSIONS
        | frozenset({
            PERM_PURCHASE_REQUESTS_CREATE, PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE,
            PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE,
            PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE,
            PERM_EPI_FEEDBACK_MANAGER_EVAL,
            PERM_EPI_EVALUATION_VIEW, PERM_EPI_EVALUATION_DECIDE, PERM_EPI_SUGGESTION_ACCEPT,
            PERM_COMPANY_SETTINGS_VIEW, PERM_COMPANY_SETTINGS_UPDATE,
        })
        | PPE_TEST_GENERAL_ADMIN_PERMISSIONS
    ),
    'registry_admin': (
        # Sem PURCHASE_ADMIN_PERMISSIONS: o Administrador de Registro cuida do
        # cadastro organizacional, não do processo de compra
        # (docs/PAPEIS_E_ATRIBUICOES.md #3: "Não cria requisições de compra.
        # Não aprova compras."). PURCHASE_VIEW_PERMISSIONS cobre a consulta
        # (relatórios cadastrais) sem conceder criação/atualização/PO.
        ADMIN_BASE_PERMISSIONS | LEGAL_ENTITY_MANAGEMENT_PERMISSIONS
        | PURCHASE_VIEW_PERMISSIONS
        | EPI_FEEDBACK_ADMIN_PERMISSIONS
        | frozenset({
            PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE,
            PERM_UNIT_LINKS_MANAGE,
            PERM_EPI_FEEDBACK_CREATE, PERM_EPI_FEEDBACK_TRIAGE, PERM_EPI_FEEDBACK_MANAGER_EVAL,
            PERM_EPI_EVALUATION_VIEW, PERM_EPI_EVALUATION_DECIDE,
        })
        | PPE_TEST_REGISTRY_ADMIN_PERMISSIONS
    ),
    'admin': (
        frozenset({
            PERM_DASHBOARD_VIEW, PERM_USERS_VIEW, PERM_UNITS_VIEW,
            PERM_EMPLOYEES_VIEW, PERM_EMPLOYEES_TRANSFER,
            PERM_EPIS_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW,
            PERM_REPORTS_VIEW, PERM_ALERTS_VIEW, PERM_STOCK_VIEW,
            # Sem PERM_EMPLOYEES_UPDATE: edição de cadastro e reativação de
            # colaborador são atribuição do Administrador de Registro
            # (docs/PAPEIS_E_ATRIBUICOES.md #3). O Administrador Local segue
            # transferindo colaboradores entre unidades da sua carteira
            # (docs/PAPEIS_E_ATRIBUICOES.md #4) via PERM_EMPLOYEES_TRANSFER.
            # Sem PERM_LEGAL_ENTITIES_VIEW: a aba CNPJs é de cadastro
            # societário (matriz, filiais, SPEs, sócias de JV) e cabe ao
            # Administrador Geral e ao Administrador de Registro. O
            # Administrador Local é perfil operacional de unidade — segue
            # consumindo o CNPJ na entrega, na ficha e no cadastro de
            # colaborador, que vêm do /api/bootstrap sem esta permissão.
            # Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — só
            # terceirizado/prestador, nunca o cadastro completo de CLT (por
            # isso é uma permissão própria, não PERM_EMPLOYEES_CREATE/UPDATE).
            PERM_EMPLOYEES_CREATE_SIMPLIFIED, PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
        })
        | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS
        | frozenset({
            PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_CREATE, PERM_EPI_EVALUATION_VIEW,
            PERM_PPE_TEST_VIEW, PERM_PPE_TEST_SUGGEST,
        })
    ),
    'buyer': (
        frozenset({
            PERM_DASHBOARD_VIEW, PERM_EPIS_VIEW, PERM_UNITS_VIEW,
            PERM_STOCK_VIEW, PERM_DELIVERIES_VIEW,
        })
        | PURCHASE_BUYER_PERMISSIONS
    ),
    'approver': (
        frozenset({
            PERM_DASHBOARD_VIEW, PERM_EPIS_VIEW, PERM_UNITS_VIEW,
            PERM_STOCK_VIEW, PERM_DELIVERIES_VIEW,
        })
        | PURCHASE_APPROVER_PERMISSIONS
    ),
    'user': (
        frozenset({
            PERM_DASHBOARD_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW,
            PERM_ALERTS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW,
            PERM_EPIS_VIEW, PERM_STOCK_VIEW,
            # Sem PERM_LEGAL_ENTITIES_VIEW: o Gestor de EPI é perfil
            # operacional de unidade e não administra o cadastro societário.
            # O CNPJ que ele precisa ver (vínculo do colaborador na ficha e na
            # entrega) chega pelo /api/bootstrap, que não exige esta permissão
            # — por isso fechar a aba não cega nenhuma tela de operação.
            # Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — ver
            # comentário equivalente no papel 'admin' acima.
            PERM_EMPLOYEES_CREATE_SIMPLIFIED, PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
        })
        | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS
        | frozenset({
            PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_TRIAGE, PERM_EPI_FEEDBACK_CREATE,
            PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_MANAGER_EVAL, PERM_EPI_EVALUATION_VIEW,
        })
        | PPE_TEST_LOCAL_ADMIN_PERMISSIONS
    ),
    'employee': frozenset({PERM_EPI_VIEW_SELF, PERM_EPI_SIGN}),
}
