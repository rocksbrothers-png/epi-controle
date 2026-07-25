# ADR-0001 — Arquitetura Multi-CNPJ / Joint Venture (LegalEntity)

- **Status:** Aceito — Fase 1 (fundação de backend) implementada
- **Data:** 2026-07-25
- **Contexto de conformidade:** jurídica, fiscal, trabalhista, previdenciária e operacional
- **Escopo desta fase:** modelo de dados, migração idempotente, API de LegalEntity,
  vínculo do colaborador ao CNPJ, campo de estrutura organizacional no onboarding,
  configuração de escopo de estoque. Fora do escopo desta fase: UI Flutter
  (Web/Android/iOS), Web legado e o cabeamento operacional completo (entregas,
  estoque, requisições, compras, relatórios, portal, QR, auditoria) — planejados
  para as fases seguintes (ver seção "Roadmap").

## 1. Contexto

Até aqui o sistema tratava, na prática, **um único CNPJ por empresa**. A tabela
`companies` acumula dois papéis: a **tenant** (cliente SaaS, fronteira de
assinatura/faturamento) e a **empresa contratante** (identidade cadastral com
`cnpj`, `legal_name`).

Esse modelo não atende grandes corporações, holdings, grupos empresariais,
multinacionais, empresas offshore e **Joint Ventures** (Petrobras, Vale, Vibra,
Modec, TechnipFMC, Altera & Ocyan JV, SBM, Halliburton, Baker Hughes, …), que
operam com **diversos CNPJs**: matriz, filiais, subsidiárias, SPEs, empresas
fiscais distintas e sócias de JV. Cada colaborador pertence **juridicamente a um
CNPJ específico**, e toda a rastreabilidade (trabalhista, previdenciária, fiscal)
depende desse vínculo.

## 2. Decisão

Introduzir uma nova entidade de domínio, **`LegalEntity`** (tabela
`legal_entities`), como fronteira **jurídica/fiscal** abaixo da empresa e acima
de unidade/colaborador. Uma empresa passa a possuir **um ou vários** CNPJs.

Nova hierarquia de rastreabilidade:

```
Tenant (SaaS)
  └── Empresa contratante        (companies)
        └── CNPJ / LegalEntity    (legal_entities)   ← NOVO
              └── Unidade          (units.legal_entity_id)
                    └── Setor
                          └── Colaborador (employees.legal_entity_id)
```

### Por que `LegalEntity` e não `CompanyTaxId`/`CompanyRegistration`

O nome **LegalEntity** é neutro em relação ao país e permite expansão futura
(ex.: EIN nos EUA, VAT na UE), enquanto `cnpj` continua sendo apenas um dos
campos. A decisão preserva a semântica "pessoa jurídica" independente do
documento fiscal.

### Relação com o modelo Multi-Tenant existente

- `companies` **continua** sendo a fronteira de tenant/assinatura. **O
  faturamento é do Tenant**; CNPJs **não** alteram a assinatura SaaS nem o
  Mercado Pago (requisito explícito).
- `legal_entities.company_id` referencia a empresa/tenant. Não criamos uma
  tabela `tenants` separada nesta fase para não fraturar o modelo atual; o
  `company_id` é a âncora de tenant. Caso a separação Tenant × Empresa seja
  formalizada no futuro, `legal_entities` já está pronta para receber um
  `tenant_id` adicional sem migração destrutiva.

## 3. Modelo de dados

Tabela `legal_entities` (idempotente via `CREATE TABLE IF NOT EXISTS`):

| Campo | Descrição |
|---|---|
| `id` | PK |
| `company_id` | FK → `companies(id)` `ON DELETE CASCADE` (empresa/tenant) |
| `cnpj` | CNPJ (validado, único por empresa) |
| `legal_name` | razão social |
| `trade_name` | nome fantasia |
| `entity_type` | `matriz`, `filial`, `subsidiaria`, `spe`, `jv_partner`, `consorciada`, `outro` |
| `parent_entity_id` | FK → `legal_entities(id)` `ON DELETE SET NULL` (holding/controladora) |
| `state_registration` | inscrição estadual |
| `municipal_registration` | inscrição municipal |
| `cnae` | CNAE |
| `address` / `municipality` / `uf` / `cep` | endereço |
| `opening_date` | data de abertura |
| `registration_status` | situação cadastral |
| `is_headquarters` | matriz (1) / filial (0) |
| `active` | ativo/inativo |
| `notes` | observações |
| `created_at` / `updated_at` | auditoria |

Colunas adicionadas (todas idempotentes, nullable ou com default):

- `companies.org_structure_type` — estrutura escolhida no onboarding
  (`single_cnpj`, `multi_cnpj`, `holding`, `group`, `joint_venture`,
  `consortium`, `other`).
- `companies.stock_control_scope` — granularidade do estoque
  (`company` | `legal_entity` | `unit`).
- `employees.legal_entity_id` — CNPJ ao qual o colaborador pertence (nullable).
- `units.legal_entity_id` — CNPJ ao qual a unidade pertence (nullable).

## 4. Migração e retrocompatibilidade (crítico)

- A migração é **idempotente** e **não-destrutiva**. Ver
  `supabase/migrations/20260725000000_legal_entities.sql`,
  `epi_backend/migrations/015_legal_entities.py` e
  `core/schema.py::ensure_legal_entities`.
- **Backfill automático:** toda empresa existente recebe uma `LegalEntity`
  padrão (matriz) a partir do `cnpj`/`legal_name` já cadastrado. Colaboradores e
  unidades sem vínculo são revinculados a essa matriz. **Nenhum dado é perdido.**
- **APIs existentes não quebram:** as colunas de vínculo são nullable e o
  `legal_entity_id` do colaborador é **opcional** no payload — quando ausente,
  cai para a matriz padrão (`resolve_employee_legal_entity_id`). Clientes atuais
  (Flutter/Web/mobile) continuam funcionando sem alteração.
- **Degradação graciosa na janela de migração:** o código consulta a existência
  da tabela/coluna (`legal_entities_ready`) antes de usar o vínculo, seguindo o
  padrão já adotado no projeto (`lifecycle_enabled`, `_table_exists`). Em um
  deploy onde o schema ainda não foi provisionado, o fluxo de CNPJ único
  continua idêntico ao anterior.

## 5. API

Novo módulo `modules/legal_entities/` (UBX / Clean Architecture: `service.py`
com regras de domínio, `routes.py` com o transporte HTTP). Endpoints:

- `GET  /api/legal-entities` — lista escopada pelo ator.
- `GET  /api/legal-entities/{id}` — item único (própria empresa).
- `GET  /api/companies/{id}/legal-entities` — CNPJs de uma empresa.
- `POST /api/legal-entities` — cadastra um CNPJ.
- `POST /api/legal-entities/batch` — **cadastro em lote** (onboarding de
  múltiplos CNPJs / Joint Venture), com erros reportados por índice.
- `PUT  /api/legal-entities/{id}` — atualiza um CNPJ.

O colaborador (`employees`) passa a expor e aceitar `legal_entity_id`, e a
listagem enriquece com `legal_entity_cnpj`/`legal_entity_name`.

## 6. Permissões (RBAC)

- `legal_entities:view` incluída em `ADMIN_BASE_PERMISSIONS` (todos os
  administradores enxergam os CNPJs da própria empresa).
- `legal_entities:{create,update,delete}` (`LEGAL_ENTITY_MANAGEMENT_PERMISSIONS`)
  concedidas a `master_admin`, `general_admin` e `registry_admin`.
- Escopo por empresa aplicado em toda escrita (`ensure_company_access`),
  atendendo o requisito: **Administrador Geral** gerencia todos os CNPJs da sua
  empresa; **Administrador Local/Usuário** enxerga apenas o(s) autorizado(s).

## 7. Consequências

**Positivas:** modelo alinhado a soluções corporativas (SAP EHS, Oracle HCM,
Sênior, TOTVS, SOGI); rastreabilidade jurídica/fiscal por CNPJ; base pronta para
holdings, grupos e JVs; zero regressão para clientes de CNPJ único (1303 testes
verdes).

**Custos/limitações:** as telas (Flutter/Web/mobile) e o cabeamento operacional
completo ficam para as próximas fases; enquanto isso o vínculo já é gravado e
rastreável no backend, mas ainda não é exposto em toda a UI.

## 8. Roadmap das próximas fases

1. **Operacional:** derivar/registrar CNPJ em entregas (via colaborador),
   estoque (respeitando `stock_control_scope`), requisições, compras, relatórios
   (filtros por Empresa/CNPJ/Unidade/Setor/Colaborador), portal do colaborador,
   QR (QR → Entrega → Colaborador → CNPJ → Empresa) e auditoria
   (`company_tax_id`/`legal_entity_id` em todos os logs).
2. **Onboarding UI:** etapa "Como sua organização está estruturada?" e o
   cadastro em lote / importação de planilha para múltiplos CNPJs e JV.
3. **Frontend:** Flutter Web, Android, iOS e Web legado — seletor de CNPJ no
   cadastro de colaborador, filtros de dashboard e exportações LGPD com
   Empresa/CNPJ/Unidade.
