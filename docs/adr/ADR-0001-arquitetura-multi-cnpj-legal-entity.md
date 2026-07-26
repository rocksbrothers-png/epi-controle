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

## 8. Fase 2 — rastreabilidade operacional (implementada)

Decisão-chave: **o CNPJ não é duplicado nas tabelas operacionais.** Ele é
sempre *derivado* do vínculo jurídico do colaborador
(`employees.legal_entity_id`), mantendo uma única fonte de verdade e evitando
divergência entre o cadastro e o histórico.

Para não repetir o gating de schema em cada módulo, o fragmento SQL é
centralizado em `employee_legal_entity_sql(connection)`
(`modules/legal_entities/service.py`), que devolve `(select, join)` — vazios
quando o schema Multi-CNPJ ainda não existe. É a fonte única usada por
colaboradores, entregas, portal e relatórios.

| Área | Comportamento |
|---|---|
| **Entregas / QR** | `fetch_deliveries` expõe `legal_entity_id`, `legal_entity_cnpj`, `legal_entity_name`, completando a cadeia **QR → Entrega → Colaborador → CNPJ → Empresa**. |
| **Unidades** | `create_unit`/`update_unit` aceitam `legal_entity_id` (keyword opcional), validando que o CNPJ pertence à empresa. Assinaturas antigas seguem válidas. |
| **Portal do colaborador** | Contexto do portal traz Empresa / CNPJ / Unidade; a auditoria registra `legal_entity_id`, `company_tax_id` e `unit_id` no payload — sem migração da tabela de auditoria. |
| **Relatórios** | Novo filtro `legal_entity_id`, aplicado sobre `employees.legal_entity_id` e sujeito ao escopo de empresa do ator. |
| **Auditoria de CNPJ** | Criação/alteração de LegalEntity grava em `company_audit_logs` (efeito fiscal/trabalhista precisa ser auditável). Falha de auditoria não desfaz a operação. |

## 9. Fase 3 — estoque, requisições e compras (implementada)

**Decisão-chave sobre estoque:** o saldo físico continua registrado *por
unidade* — é onde o item de fato está. O `stock_control_scope` define apenas a
**fronteira de compartilhamento** do saldo, não a chave de armazenamento:

| Escopo | Pool de estoque |
|---|---|
| `unit` | só a própria unidade (comportamento histórico) |
| `legal_entity` | todas as unidades do mesmo CNPJ |
| `company` | todas as unidades da empresa (estoque compartilhado) |

Como cada unidade já carrega `legal_entity_id`, o pool por CNPJ é **derivado**
(`resolve_stock_pool_unit_ids`) — sem re-chavear `unit_epi_stock` e sem migração
de dados. Um re-chaveamento seria destrutivo e obrigaria a reconciliar todo o
histórico; a derivação entrega a mesma semântica com risco zero de perda.

`fetch_scoped_stock_balance` devolve o saldo agregado do pool **e** a composição
por unidade, para conferência operacional.

> **Escopo deliberadamente não alterado:** a *baixa* de estoque na entrega
> continua ocorrendo na unidade da operação. Tornar a baixa multi-unidade muda
> comportamento crítico de negócio (qual unidade é debitada quando o pool é
> compartilhado) e exige decisão do cliente sobre a ordem de consumo — fica para
> uma fase própria, validada.

**Requisições** registram Empresa / CNPJ / Unidade / Solicitante com o CNPJ
*derivado* do solicitante, coerente com a Fase 2 — sem coluna redundante.

**Pedidos de compra** são a exceção justificada: `purchase_orders.legal_entity_id`
é coluna própria (migration 016), porque o CNPJ emissor é uma **escolha no
momento da emissão**, não um dado derivável. `NULL` = pedido da empresa
(comportamento histórico).

**Configuração** (`org_structure_type`, `stock_control_scope`) exposta em
*Minha Empresa*, atendendo a tela "Controlar estoque por: Empresa / CNPJ /
Unidade". Valores fora do enum caem no padrão em vez de quebrar a tela.

## 10. Fase 4 — conformidade: escopo, obrigatoriedade, auditoria e ciclo de vida

**Escopo de visibilidade por CNPJ** (`resolve_actor_legal_entity_ids`):

| Papel | Alcance |
|---|---|
| Master / Geral / Registro | todos os CNPJs da empresa |
| Administrador Local (`admin`) | apenas os CNPJs autorizados em `user_legal_entities` |
| Usuário (`user`) | apenas o CNPJ do colaborador vinculado (derivado de `linked_employee_id`) |

> **Decisão de retrocompatibilidade:** para o Administrador Local, **lista de
> autorização vazia = sem restrição**. Administradores locais já existentes
> nunca tiveram autorização explícita; tratá-los como "sem acesso a nada" os
> deixaria travados no primeiro deploy. A restrição passa a valer assim que o
> Administrador Geral atribui CNPJs ao usuário
> (`PUT /api/users/{id}/legal-entities`).

O guard `ensure_legal_entity_access` aplica o escopo nas leituras/escritas de
CNPJ; `fetch_legal_entities` filtra a listagem.

**CNPJ obrigatório no colaborador** — exigido **quando a empresa tem mais de um
CNPJ ativo**. Empresa de CNPJ único mantém o fallback automático para a matriz.
Escolher a matriz por omissão numa empresa multi-CNPJ registraria o vínculo
trabalhista/previdenciário na pessoa jurídica errada; exigir sempre quebraria
todos os clientes atuais. A regra condicional resolve os dois.

**Auditoria** — `company_audit_logs.legal_entity_id` (migration 017) registra o
CNPJ afetado; `NULL` = ação no nível da empresa.

**Ciclo de vida do CNPJ** — `DELETE /api/legal-entities/{id}` é **inativação
auditada**, nunca exclusão física: o histórico jurídico/fiscal deve sobreviver.
Bloqueia quando é o último CNPJ ativo ou quando há colaboradores vinculados
(exige realocação antes).

**LGPD** — o snapshot da ficha passa a informar o CNPJ **jurídico do
colaborador** (com o da empresa contratante como fallback), além de Empresa e
Unidade.

## 11. Fase 5 — CNPJ imutável e transferência administrativa (implementada)

**Decisão de negócio do cliente:** o CNPJ representa o **vínculo jurídico do
contrato de trabalho** e é **imutável após a admissão**. A unidade representa
apenas a **lotação operacional**.

Consequências implementadas:

| Regra | Implementação |
|---|---|
| Transferência de unidade nunca altera o CNPJ | `update_employee_unit` toca somente `unit_id` — verificado e documentado; nenhuma lógica automática foi criada |
| CNPJ imutável na edição comum | `update_employee` **ignora** `legal_entity_id` do payload e preserva o vínculo da admissão |
| Alteração só por processo administrativo | `POST /api/employees/{id}/legal-entity-transfer`, com justificativa obrigatória |
| Auditoria completa | Registro em `employee_legal_entity_movements` (migration 018) + `company_audit_logs` com o CNPJ afetado |
| Histórico preservado | O histórico é cumulativo (`GET /api/employees/{id}/legal-entity-movements`); nada é sobrescrito |
| Operações usam a unidade atual | Estoque, entrega e movimentações continuam ancorados na lotação operacional vigente |

A permissão `employees:legal_entity_transfer` restringe o processo a
Administrador Master / Geral / de Registro.

Colaborador legado sem vínculo recebe o backfill para a matriz na primeira
edição — não é uma "alteração" de CNPJ, e sim a materialização do vínculo que
já existia implicitamente.

## 12. Roadmap das próximas fases

1. **Baixa de estoque multi-unidade:** definir e implementar a ordem de consumo
   quando o pool é compartilhado (FEFO entre unidades? unidade da operação
   primeiro?). Exige decisão de negócio do cliente.
2. **Importação de planilha de CNPJs** e **filtros hierárquicos de dashboard**
   (Empresa → CNPJ → Unidade → Setor).
3. **Onboarding UI:** etapa "Como sua organização está estruturada?" e o
   cadastro em lote / importação de planilha para múltiplos CNPJs e JV
   (backend de lote já disponível em `POST /api/legal-entities/batch`).
3. **Frontend:** Flutter Web, Android, iOS e Web legado — seletor de CNPJ no
   cadastro de colaborador, filtros de dashboard e exportações LGPD com
   Empresa/CNPJ/Unidade.
