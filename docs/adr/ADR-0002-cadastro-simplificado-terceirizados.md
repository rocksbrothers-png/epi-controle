# ADR-0002 — Cadastro Simplificado de Terceirizados e Prestadores

- **Status:** Aceito e implementado — PR 1 (fundação), PR 3 (cadastro do
  colaborador), PR 4 (snapshot na entrega), PR 5 (auditoria de
  responsabilidade), PR 6 (relatórios, ressarcimento, alerta de migração),
  PR 7 (Flutter), PR 8 (Web Legado) e PR 9 (regressão de ponta a ponta e
  documentação final) — sequência completa. Estendido pela §10 (Cadastro de
  Colaboradores, Arquivamento e Escopo por Unidade): PR 10 (fundação —
  módulo `terceirizados_colaboradores`, permissões simplificadas, schema de
  `module_unit_scope`), PR 11 (rota do Cadastro de Colaboradores
  simplificado), PR 12 (arquivamento de `outsourced_companies`), PR 13
  (Colaboradores Arquivados + relatório de headcount + bloqueio de entrega),
  PR 14 (Flutter) e PR 15 (Web Legado) — sequência completa, ver §10.6.
  Estendido novamente pela §11 (CRUD de empresas terceirizadas
  descentralizado por Unidade): piso técnico com OR entre
  `employees:create`/`create_simplified`, `ensure_module_enabled_for_unit`
  como autoridade real de escrita em `outsourced_companies`, coluna
  `outsourced_companies.unit_id`, e correção da lacuna de
  arquivar/reativar Colaborador Terceirizado por `admin`/`user`.
- **Data:** 2026-08-05
- **Contexto de conformidade:** trabalhista, previdenciária, fiscal e operacional (EPI)
- **Escopo desta fase (PR 1):** auditoria da arquitetura existente, modelo de
  dados, migração idempotente, entidade `outsourced_companies` +
  `service_contracts`, escopo multi-tenant, constraints/enums/índices,
  permissões (reaproveitadas), `module_visibility` (módulo `terceirizados`,
  oculto por padrão), testes unitários e de isolamento. **Fora do escopo
  desta fase:** integração com o fluxo de entrega (snapshot histórico),
  relatórios financeiros/ressarcimento, telas finais de UI (Flutter/Web
  legado) — planejados para as fases seguintes (ver seção "Roadmap").

## 1. Contexto

O sistema hoje cobre bem o colaborador **CLT**, mas o cadastro completo é
pesado demais para o caso comum de **terceirizados e prestadores de
serviço** que precisam de EPI rapidamente — muitas vezes em caráter
temporário ou emergencial. O pedido do produto: um cadastro rápido, sem
duplicar a base de colaboradores, sem duplicar o fluxo de entrega, ficha,
estoque, QR Code, auditoria ou relatórios, e sem criar um segundo sistema
paralelo.

### O que a auditoria encontrou

A boa notícia: a arquitetura já pratica boa parte do princípio central do
pedido.

- `employees.tipo_vinculo` já aceita `Terceirizado` e `Prestador de
  Serviço`, com `employees.empresa_origem` ao lado (texto livre) —
  adicionados numa rodada anterior deste mesmo projeto.
- `modules/reports/service.py` já agrupa e filtra entregas por
  `tipo_vinculo` (`by_tipo_vinculo`).
- Entrega, ficha de EPI, QR Code, estoque e auditoria não bifurcam por tipo
  de vínculo — o terceirizado já passa pelo mesmo caminho de código que o
  CLT, porque é a mesma linha na mesma tabela `employees`.
- `module_visibility` (ADR anterior, mesma sessão) já dá ao Administrador
  Geral o mecanismo exato pedido para gatear uma subpasta nova por perfil.
- `register_company_audit()` aceita `action_type` livre — não exige schema
  novo de auditoria.

O que faltava: (1) transformar `empresa_origem` de texto livre em uma
entidade pesquisável com CNPJ e contrato, (2) um cadastro de poucos campos
que grava direto nas tabelas existentes, (3) um campo de responsabilidade
pelo fornecimento de EPI com herança e exceção, (4) suporte a múltiplos
contratos por empresa sem duplicar seu cadastro.

## 2. Decisão

### 2.1 Onde mora a empresa terceirizada — três alternativas de reaproveitamento testadas e rejeitadas

A prioridade explícita, antes de aceitar uma tabela nova: reutilizar o
cadastro de empresas existente sempre que possível. Três alternativas reais
foram testadas contra o schema, não hipoteticamente.

**Rejeitada — nova linha em `companies`.** `companies` é o tenant do SaaS —
plano, limite de usuário, login próprio; `company_id` é a própria fronteira
de isolamento multi-tenant usada em todo o sistema. Uma terceirizada não
assina o EPI Controle; criar uma linha aqui criaria um tenant fantasma.

**Rejeitada — novo valor de `legal_entities.entity_type`.** Esta era a
alternativa mais promissora: `entity_type` já aceita `jv_partner` e
`consorciada` (empresas parceiras, não filiais do tenant), e `entity_type`
não alimenta nenhuma regra de escopo de JV (confirmado em `epi_scope.py`) —
é extensível sem quebrar nada por si só. O bloqueio real está em
`employees.legal_entity_id`: pelo comentário de
`resolve_employee_legal_entity_id()` no código, este campo representa o
**vínculo trabalhista/previdenciário** — qual CNPJ *do próprio tenant*
assina a carteira do colaborador. Apontar esse campo para uma terceirizada
diria ao sistema "este CNPJ é uma filial minha e emprega esta pessoa", o
que é juridicamente falso para um terceirizado. Reaproveitar exigiria
corromper esse campo ou criar uma segunda coluna de referência do mesmo
jeito — perdendo o ganho de reaproveitar `legal_entities`.

**Rejeitada — reaproveitar `authorized_suppliers`.** Estruturalmente a mais
parecida: tabela pequena, por tenant, com `name`/`cnpj`/`category`/contato/
auditoria — validando que este é o padrão certo de "referência a empresa
externa" nesta base de código. Mas está profundamente acoplada ao fluxo de
Compras: FK em pedido de compra e cotação (RFQ), e login próprio de portal
(`supplier_portal_links`, `supplier_portal_audit_logs`). Colocar uma
terceirizada de mão de obra aqui a faria aparecer em dropdown de pedido de
compra e ganhar acesso a um portal de cotação — misturaria "quem me vende
EPI" com "quem me empresta gente".

**Escolhida — nova tabela de referência leve, no mesmo padrão que
`authorized_suppliers` já validou.** Pequena, sem hierarquia, sem billing,
sem portal próprio, sem RLS de tenant: apenas `company_id` (tenant
contratante) + atributos da empresa terceirizada. `employees.empresa_origem`
permanece como está nesta fase (compatibilidade); `employees.
outsourced_company_id` é a nova referência (FK, nullable — `NULL` para todo
CLT). `employees.legal_entity_id` **não é tocado**: continua exclusivamente
o vínculo trabalhista/previdenciário com um CNPJ do próprio tenant.

### 2.2 Não-metas — o que `outsourced_companies` nunca vai ser

Declarado explicitamente como condição vinculante da aprovação, não como
decorrência implícita do desenho. `outsourced_companies` e o que a
acompanha **não** criam:

1. um segundo banco de dados nem schema isolado;
2. um segundo cadastro-mestre de pessoas — `employees` continua a única
   tabela de colaboradores, sem `outsourced_employees` ou equivalente;
3. um segundo fluxo de entrega de EPI;
4. uma segunda ficha de EPI;
5. um segundo controle de estoque;
6. uma auditoria independente — usa `register_company_audit()`;
7. um sistema de relatórios paralelo — estende os relatórios existentes;
8. um modelo de permissões próprio — usa `module_visibility` e os papéis já
   existentes.

## 3. Modelo de dados

### 3.1 Escopo multi-tenant

`outsourced_companies` não é um tenant e não tem RLS própria, mas toda linha
carrega `company_id` (o tenant contratante) como fronteira de isolamento
obrigatória — mesmo padrão de `legal_entities`/`authorized_suppliers`. Toda
query passa pelo filtro de escopo existente. CNPJ é armazenado normalizado
(`cnpj_normalized`, só dígitos) com um **índice único parcial**
`(company_id, cnpj_normalized) WHERE cnpj_normalized <> ''` (mesmo padrão já
usado por `idx_deliveries_idempotency`): a mesma terceirizada nunca duplica
dentro do mesmo tenant quando o CNPJ é conhecido, o mesmo CNPJ pode aparecer
em tenants diferentes sem colisão (unicidade composta, não global), e — por
ser parcial — mais de uma terceirizada do mesmo tenant pode estar sem CNPJ
ao mesmo tempo (Cadastro Simplificado emergencial). Um `UNIQUE` de tabela
simples bloquearia esse último caso, porque duas linhas com
`cnpj_normalized = ''` colidiriam entre si — corrigido ainda no PR 1 antes
da wiring do PR 3 revelar o problema em teste.

### 3.2 Nomenclatura

Convenção geral (herdada de `tipo_vinculo`): rótulo em português gravado
direto na coluna. **Exceção vinculante:** `company_kind` usa valores
técnicos estáveis em **inglês**, com o rótulo em português só na camada de
UI — para não acoplar um enum estrutural ao texto exibido.

| `company_kind` (gravado) | Rótulo exibido (PT-BR, só UI) |
|---|---|
| `outsourced` | Terceirizada |
| `service_provider` | Prestadora de Serviço |
| `other_contracted` | Outro |

Sem `Empresa Própria` (CLT = `outsourced_company_id IS NULL`) nem
`Fornecedor` (nome já usado por `authorized_suppliers`, outro domínio).

`epi_responsibility` (PT-BR, sem troca de convenção — vive uma vez na
empresa, referenciado por Simplificado/Padrão, nunca duplicado):

`Empresa Contratante` · `Empresa Terceirizada` · `Empresa Prestadora de
Serviço` · `Responsabilidade Compartilhada` · `Conforme Contrato` (default)
· `Não Definido`.

`registration_mode`: `simplified` | `standard`.
`registration_status`: `pending_completion` | `complete` | `inactive` | `archived`.

### 3.3 Schema

```sql
CREATE TABLE outsourced_companies (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id           INTEGER NOT NULL,           -- tenant contratante (FK companies)
    legal_name           TEXT NOT NULL,
    trade_name           TEXT NOT NULL DEFAULT '',
    cnpj                 TEXT NOT NULL DEFAULT '',    -- como digitado, para exibição
    cnpj_normalized       TEXT NOT NULL DEFAULT '',    -- só dígitos, para unicidade/busca
    company_kind         TEXT NOT NULL DEFAULT 'outsourced',
    epi_responsibility    TEXT NOT NULL DEFAULT 'Conforme Contrato',
    registration_mode     TEXT NOT NULL DEFAULT 'simplified',
    registration_status   TEXT NOT NULL DEFAULT 'pending_completion',
    status               TEXT NOT NULL DEFAULT 'Ativa',
    promoted_at          TEXT NOT NULL DEFAULT '',
    created_by_user_id    INTEGER,
    created_at           TEXT NOT NULL DEFAULT '',
    updated_at           TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- unicidade só quando o CNPJ é conhecido — índice parcial, não UNIQUE de
-- tabela (ver §3.1: duas terceirizadas do mesmo tenant sem CNPJ não colidem)
CREATE UNIQUE INDEX uq_outsourced_companies_company_cnpj
    ON outsourced_companies (company_id, cnpj_normalized)
    WHERE cnpj_normalized <> '';

-- contrato: uma outsourced_company pode ter N contratos (unidades/períodos
-- diferentes) sem duplicar o cadastro da empresa
CREATE TABLE service_contracts (
    id                             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id                     INTEGER NOT NULL,
    outsourced_company_id          INTEGER NOT NULL,
    unit_id                        INTEGER,            -- NULL = vale para todas as unidades
    contract_ref                   TEXT NOT NULL DEFAULT '',
    start_date                     TEXT NOT NULL DEFAULT '',
    end_date                       TEXT NOT NULL DEFAULT '',
    epi_responsibility_override     TEXT NOT NULL DEFAULT '',  -- vazio = herda o default da empresa
    override_reason                TEXT NOT NULL DEFAULT '',
    status                         TEXT NOT NULL DEFAULT 'Ativo',
    created_by_user_id              INTEGER,
    created_at                     TEXT NOT NULL DEFAULT '',
    updated_at                     TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (outsourced_company_id) REFERENCES outsourced_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- employees: referência à empresa terceirizada/contrato (nullable = CLT)
ALTER TABLE employees ADD COLUMN outsourced_company_id INTEGER;
ALTER TABLE employees ADD COLUMN service_contract_id INTEGER;
-- exceção individual de responsabilidade, com motivo obrigatório na
-- camada de serviço quando preenchida
ALTER TABLE employees ADD COLUMN epi_responsibility_override TEXT NOT NULL DEFAULT '';
ALTER TABLE employees ADD COLUMN epi_responsibility_override_reason TEXT NOT NULL DEFAULT '';

-- employees.legal_entity_id NÃO é tocado — continua exclusivamente o CNPJ
-- do PRÓPRIO tenant que detém o vínculo trabalhista/previdenciário
```

Migração idempotente via `_safe_add_column`/`CREATE TABLE IF NOT EXISTS`,
mesmo padrão de `core/schema.py` hoje — só complemento, nenhuma coluna
existente é removida, renomeada ou perde significado.

### 3.4 Limiar Simplificado/Padrão — configurável, nunca hardcoded

O alerta de sugestão de migração usa um limiar de duração (em dias)
configurável por tenant via `configuration_framework` (mesmo storage do
`module_visibility`) — default de sistema de 30 dias quando o tenant não
configurou nada. Fica para o PR de alertas (fora do escopo do PR 1); o
contrato de leitura já é documentado aqui.

### 3.5 Snapshot histórico na entrega (fora do escopo do PR 1)

Editar a empresa terceirizada ou o contrato depois de uma entrega já feita
não pode alterar o que aquela entrega significa historicamente. A entrega
vai gravar, no momento em que acontece, uma cópia denormalizada dos
atributos relevantes (`snapshot_tipo_vinculo`,
`snapshot_outsourced_company_name`, `snapshot_outsourced_company_cnpj`,
`snapshot_contracting_company_id`, `snapshot_contract_ref`,
`snapshot_epi_responsibility`) — preenchida uma vez na escrita, nunca
recalculada a partir do estado atual. Isto pertence ao PR de integração com
entrega, citado aqui para deixar claro o contrato de dados que este PR 1
precisa deixar pronto (as colunas de origem que o snapshot vai copiar).

### 3.6 Ressarcimento (fora do escopo do PR 1)

Registro de apoio, não cobrança automática. Enum de status ampliado:
`Não Aplicável` · `Pendente de Análise` · `Passível de Ressarcimento` ·
`Apta para Cobrança` · `Incluída em Relatório` · `Ressarcida` ·
`Contestada` · `Dispensada`.

## 4. Controle de acesso

Módulo novo em `module_visibility`: `terceirizados`, com
`MODULE_REQUIRED_PERMISSIONS['terceirizados'] = {employees:create}` — mesmo
teto técnico de quem já cria colaborador hoje (master_admin, general_admin,
registry_admin). As rotas HTTP reaproveitam diretamente `employees:view` /
`employees:create` / `employees:update` — nenhum modelo de permissão novo.

**Condição vinculante:** a subpasta nasce **oculta por padrão**, para todo
papel, mesmo para quem já tem `employees:create` — até o Administrador
Geral ligá-la explicitamente por tenant. Implementado em
`epi_backend/rule_engine.py` via `_OPT_IN_MODULES`, que soma-se às
restrições estruturais existentes (`_STRUCTURALLY_HIDDEN_BY_DEFAULT`) na
construção da visibilidade padrão do sistema.

## 5. Auditoria

Mesma função `register_company_audit()`, novos `action_type`:
`outsourced_company_created`, `outsourced_company_updated`,
`outsourced_company_promoted`, `service_contract_created`,
`epi_responsibility_changed`, `epi_responsibility_override_set`,
`epi_reimbursement_recorded`. Zero schema novo de auditoria.

## 6. Fluxo de UX (referência — telas fora do escopo do PR 1)

Nova subpasta dentro de **Cadastro de Colaborador**: **Terceirizados e
Prestadores**. Cadastro Simplificado da empresa (Razão Social, CNPJ
opcional, Tipo, Responsabilidade, Situação) e do trabalhador (mesma
`create_employee`, campos mínimos). Migração Simplificado → Padrão é
`UPDATE` na mesma linha (`registration_mode`, `registration_status`,
`promoted_at`) — nunca `INSERT`, nunca perde histórico. Depois do cadastro,
o trabalhador entra no fluxo existente de entrega/ficha/estoque/QR/
relatórios sem nenhuma mudança de código nesses fluxos.

## 7. Plano de implementação — PRs por camada de responsabilidade

1. **PR 1 (este) — Fundação.** Tabelas `outsourced_companies` e
   `service_contracts`; colunas novas em `employees`; escopo multi-tenant e
   `UNIQUE(company_id, cnpj_normalized)`; enums (`company_kind` em inglês,
   `registration_mode`/`registration_status`); índices; módulo
   `terceirizados` em `module_visibility` (oculto por padrão); testes
   unitários e de isolamento multi-tenant; este documento. **Fora deste
   PR:** fluxo de entrega (incluindo colunas de snapshot), relatórios
   financeiros/ressarcimento, telas finais de UI. Zero mudança de
   comportamento visível até alguém ligar o módulo.
2. **PR 2 — Cadastro das empresas.** `GET/POST/PUT /api/outsourced-companies`
   e `POST .../promote` já implementados no PR 1 como fundação — cobre
   Simplificado (CNPJ opcional) e Padrão (CNPJ obrigatório) na mesma função
   de gravação. Sem gap adicional de API; a apresentação em tela fica com os
   PRs 7/8.
3. **PR 3 (implementado) — Cadastro dos colaboradores + validações.**
   `create_employee`/`update_employee` aceitam, opcionalmente,
   `outsourced_company_id`/`service_contract_id`/
   `epi_responsibility_override(_reason)`, validados por
   `validate_employee_outsourced_reference` (mesmo tenant; contrato
   pertence à empresa informada; override exige motivo) — mesma função que
   o cadastro completo já usa, sem caminho de código novo. `GET /api/employees`
   e `GET /api/employees/{id}` devolvem as colunas novas. Corrigido, nesta
   mesma leva, um bug real descoberto pelos testes: o índice de unicidade de
   CNPJ era `UNIQUE` de tabela em vez de parcial, e bloqueava uma segunda
   terceirizada sem CNPJ no mesmo tenant — ver §3.1.
4. **PR 4 (implementado) — Integração com o fluxo existente de entrega.**
   Seis colunas `snapshot_*` novas em `deliveries` (§3.5), preenchidas uma
   única vez por `resolve_delivery_outsourced_snapshot` no momento da
   criação da entrega — `create_delivery_service` ganhou uma leitura a
   mais antes do `INSERT`, nenhuma bifurcação de lógica. Vazio (exceto
   `tipo_vinculo`) para colaborador CLT. Testado que editar a empresa/
   contrato depois de uma entrega já registrada não altera o snapshot já
   gravado — a garantia central deste PR.
5. **PR 5 (implementado) — Auditoria, histórico e registro de
   responsabilidades.** Além de `outsourced_company_created/updated/
   promoted` e `service_contract_created` (já no PR 1), dois eventos
   dedicados: `epi_responsibility_changed` — quando o default da empresa
   muda, emitido junto com o `outsourced_company_updated` genérico, para
   permitir filtrar o histórico só por essa mudança específica — e
   `epi_responsibility_override_set` — quando a exceção individual do
   colaborador é criada, alterada ou removida. Ambos só disparam quando o
   valor de fato muda, nunca a cada create/update. `register_company_audit()`
   segue sendo a única função de auditoria — zero schema novo.
6. **PR 6 (implementado) — Relatórios, ressarcimento, alerta de migração.**
   Relatório de entregas ganha três dimensões novas —
   `by_outsourced_company`, `by_epi_responsibility`, `by_delivering_company`
   — lidas do snapshot histórico gravado na entrega (PR 4), mais dois
   filtros (`outsourced_company_name`, `epi_responsibility`); exportação em
   PDF também as inclui. Tabela `epi_reimbursements` (registro de apoio,
   sem cobrança automática) com o enum de 8 estados do §3.6, unicidade por
   entrega (`UNIQUE(delivery_id)`), endpoints
   `GET/POST /api/epi-reimbursements` e
   `PUT /api/epi-reimbursements/{id}/status`. Alerta de sugestão de
   migração Simplificado → Padrão (`GET /api/outsourced-companies/
   migration-suggestions`) usa o limiar configurável já documentado no §3.4
   — passou a existir de fato em `default_framework_payload()`
   (`outsourced_simplified_duration_threshold_days`, default 30 dias),
   sugestão nunca bloqueio. Dashboards de UI ficam para os PRs de Flutter/
   Web legado (7/8) — este PR cobre só a API.
7. **PR 7 — Flutter (Web, Android, iOS). (implementado)** Tela
   `OutsourcedCompaniesScreen` + `OutsourcedCompaniesCubit` no app
   `epi_admin`, espelhando exatamente o padrão de CNPJs (LegalEntity):
   modelos `OutsourcedCompany`/`ServiceContract`/`MigrationSuggestion`/
   `EpiReimbursement` no pacote `epi_api` com `fromJson`/`toJson`;
   `OutsourcedCompaniesApi` cobrindo todo o CRUD do §7 (PR6); listagem com
   busca, formulário único de criar/editar e confirmação de promoção
   Simplificado → Padrão. Rota `/outsourced-companies` cadastrada com
   `module_visibility: 'terceirizados'` (oculto por padrão, opt-in) e piso
   técnico `employees:create` (sem permissão dedicada, por decisão deste
   ADR). 22 chaves de i18n traduzidas nos 5 locales region-specific.
8. **PR 8 — Web Legado. (implementado)** Nova tela `#terceirizados-view`
   (padrão de abas Cadastro/Lista, igual à de CNPJs) em `static/`, montada
   via fragmentos (`static/views/terceirizados.html`, `_sidebar.html`,
   `_scripts.html`, `scripts/build_index.py`). Regras puras em
   `static/js/views/outsourced-companies-view.js` (rótulo de tipo, filtro de
   lista, `canPromote`), testadas em `static/js/test/run-tests.js`. Estado
   (`state.outsourcedCompanies`) carregado sob demanda ao abrir a tela — não
   entra no `/api/bootstrap`, pois o módulo nasce oculto por padrão
   (`VIEW_MODULE.terceirizados: 'terceirizados'`). CRUD via
   `saveSimpleForm`/`api()` reaproveitando os endpoints do PR1, incluindo
   promoção Simplificado → Padrão com confirmação. 22 chaves de i18n
   traduzidas nos 5 locales de `static/i18n/`.
9. **PR 9 — Testes completos, regressão e documentação final. (implementado)**
   `tests/test_outsourced_companies_end_to_end_journey.py`: regressão de
   ponta a ponta amarrando PR1+PR3+PR4+PR5+PR6 num único fluxo contínuo —
   cadastro Simplificado sem CNPJ → promoção recusada sem CNPJ → entrega com
   snapshot congelado → mudança de responsabilidade audita mas não reescreve
   o snapshot já gravado → ressarcimento ligado à entrega real → sugestão de
   migração após o limiar configurado → CNPJ preenchido e promoção ao
   Cadastro Padrão bem-sucedida → isolamento multi-tenant (mesmo CNPJ em
   dois tenants, nenhum dado vaza). `tests/test_outsourced_companies_legacy_
   web_wiring.py`: garante que a tela do PR8 está de fato acessível a partir
   do `index.html` gerado (nav, module_visibility, formulário, script,
   i18n) — mesmo padrão de `tests/test_legal_entity_legacy_web_wiring.py`.
   Este ADR foi atualizado como documentação final: todos os 9 PRs da
   sequência aprovada estão marcados "(implementado)" nesta seção, cada um
   com o resumo técnico do que foi entregue.

Critério de aceite em cada PR: suíte completa (`pytest`, `flutter
analyze`/`test`, runner JS) verde, mais teste manual em navegador antes de
qualquer PR de UI ir para revisão.

## 8. Riscos identificados

| Risco | Mitigação |
|---|---|
| Backfill futuro de `empresa_origem` (texto livre) cria terceirizadas duplicadas por variação de digitação | Normalização + revisão manual antes de qualquer backfill em produção; tela de "mesclar empresas" se o volume justificar |
| CNPJ pode não ser conhecido no cadastro simplificado (serviço emergencial) | CNPJ opcional no Simplificado, obrigatório no Padrão e na promoção (`promote_outsourced_company` valida) |
| Ressarcimento vira, sem querer, uma cobrança de verdade | Sem qualquer integração de pagamento/fatura — só registro para conferência manual |
| Migração Simplificado → Padrão perder histórico | Migração é `UPDATE` na mesma linha, nunca `INSERT` — coberto por teste dedicado (`test_promote_requires_cnpj_and_updates_registration_fields`) |
| Módulo opt-in esquecido em `MODULE_KEYS`/`MODULE_REQUIRED_PERMISSIONS` causa 404 silencioso na config | Testes dedicados em `tests/test_module_visibility.py` cobrem a presença e o comportamento oculto-por-padrão de `terceirizados` |

## 9. Roadmap

PRs 2–9 descritos na seção 7, cada um com o mesmo rigor de testes e revisão
manual de UI aplicado nesta e nas fases anteriores do projeto.

## 10. Extensão — Cadastro de Colaboradores, Arquivamento e Escopo por Unidade

Com os 9 PRs da fundação implantados, o pedido de produto evoluiu para três
capacidades novas dentro do módulo "Terceirizados e Prestadores", sempre
reaproveitando a arquitetura já estabelecida — nenhuma delas introduz um
modelo de dados paralelo, um novo mecanismo de autorização, ou uma segunda
fonte de verdade.

### 10.1 Cadastro de Colaboradores (simplificado)

Nova aba dentro do módulo para cadastrar colaboradores terceirizados/
prestadores diretamente pela unidade, sem passar pelo formulário completo
de RH. Grava na MESMA tabela `employees` (nunca uma tabela paralela) — o
colaborador criado por este formulário é indistinguível, para o resto do
sistema (entrega, ficha, auditoria, relatórios), de um criado pelo
Cadastro de Colaborador completo.

Campos obrigatórios: nome, CPF, empresa terceirizada/prestadora
(`outsourced_company_id`, agora obrigatório neste fluxo — no formulário
completo continua opcional), unidade, função, tipo de vínculo (restrito a
`Terceirizado`/`Prestador de Serviço` — CLT nunca é aceito por este
formulário), data de início.

Campos opcionais novos: matrícula da empresa de origem
(`employees.origin_company_registration`), crachá (`employees.
badge_number`), observações (`employees.notes`).

**Contrato, Ordem de Serviço e Data prevista de término reaproveitam
`service_contracts`** (já existente desde o PR1 da fundação), em vez de
ganharem colunas próprias em `employees`: `service_contracts.contract_ref`
= "Contrato", `service_contracts.end_date` = "Data prevista de término"
(já é exatamente esse conceito), e a única peça genuinamente nova é
`service_contracts.service_order_ref` = "Ordem de Serviço" (não havia
campo equivalente). `employees.service_contract_id` já existia para ligar
o colaborador ao contrato. Duplicar esses três campos em `employees`
criaria duas fontes de verdade divergentes para o mesmo fato — contrário
ao princípio desta ADR.

### 10.2 Permissões — reaproveitadas, não ampliadas

Administrador Local (`admin`) e Gestor de EPI (`user`) hoje não têm
`employees:create`/`employees:update` — decisão deliberada e documentada
em `core/permissions.py` (edição de cadastro é atribuição do Administrador
de Registro). Em vez de conceder essas permissões amplas — o que abriria o
cadastro COMPLETO de CLT para esses papéis, muito além do pedido —,
criamos duas permissões novas e estreitas, exclusivas deste fluxo:
`employees:create_simplified` e `employees:update_simplified`, concedidas
a `admin`/`user`, checadas apenas nas rotas do Cadastro de Colaboradores
simplificado. `create_employee`/`update_employee` (a função real que grava
no banco) permanecem inalteradas — sem lógica paralela, só um piso de
permissão diferente na rota de entrada.

### 10.3 Visibilidade — reaproveitada e estendida com escopo por unidade

**Nenhum mecanismo novo de visibilidade foi criado.** A tela permanece
oculta por padrão em todo tenant (módulo opt-in, mesmo tratamento de
`terceirizados`) até o Administrador Geral autorizar explicitamente — e a
autorização usa o `module_visibility` já existente
(`epi_backend/rule_engine.py`, storage em `configuration_framework`,
edição via `modules/settings/service.py::save_module_visibility`), sem
tabela nova, sem sistema de autorização paralelo.

A melhoria pedida — autorizar por Unidade, não só por perfil/tenant — foi
implementada como uma extensão mínima e retrocompatível do mesmo
mecanismo:

- Novo módulo dedicado `"terceirizados_colaboradores"` em `MODULE_KEYS`
  (piso técnico `employees:create_simplified`), tratado como opt-in
  exatamente como `terceirizados`.
- Nova chave `module_unit_scope: {module: [unit_id, ...]}` no mesmo
  `configuration_framework` que já guarda `module_visibility` — não uma
  tabela nova, um campo a mais no mesmo JSON por tenant. Lista vazia ou
  ausente (o padrão para TODOS os módulos existentes) significa "sem
  restrição de unidade" — comportamento de todo módulo anterior a esta
  extensão permanece 100% inalterado.
- `resolve_module_visibility()` ganha uma terceira condição, além de
  "configurado" e "permissão técnica": quando o módulo tem unidades
  configuradas em `module_unit_scope` E o ator é `admin`/`user`, a unidade
  operacional atual do ator (`modules.employees.service.
  actor_operational_unit_id` — o mesmo resolvedor já usado em entregas,
  fichas, alertas e compras para escopar esses papéis à própria unidade)
  precisa estar na lista autorizada. `general_admin`/`registry_admin`/
  `master_admin` não são escopados por unidade (já é assim em todo o
  sistema) e não são afetados por essa checagem.
- Reaproveita a premissa já documentada em `actor_operational_unit_id`:
  Administrador Local e Gestor de EPI têm vínculo único com UMA unidade
  (nunca uma carteira de várias) — por isso a UI do Administrador Geral
  não atribui unidades a um usuário específico, e sim autoriza QUAIS
  unidades têm o módulo ligado; cada Admin Local/Gestor de EPI só enxerga
  o módulo se a única unidade em que já opera estiver na lista.
- **Backend é a autoridade real, não só o menu**: as rotas de escrita do
  Cadastro de Colaboradores simplificado e do CRUD de empresas
  terceirizadas validam o mesmo escopo (unidade do ator dentro da lista
  autorizada do módulo, e — para colaborador — unidade do colaborador
  igual à unidade do ator) mesmo que o frontend nunca chegue a mostrar o
  menu. Nenhuma rota de dados passa a confiar em `module_visibility`/
  `module_unit_scope` para autorizar — eles só orientam menu/rotas/deep
  links, como já documentado no docstring de `resolve_module_visibility`.

### 10.4 Arquivamento

`outsourced_companies` ganha o mesmo ciclo de vida genérico já usado por
`employees`/`units`/`epis` (`core/archival.py`: `archive_record`,
`restore_record`, `request_purge`/`cancel_purge`/`confirm_purge`,
`ensure_record_operational`) — mesmas 10 colunas de lifecycle
(`status/archived_at/archived_by/archive_reason/retention_until/
legal_hold/legal_hold_reason/deleted_at/deleted_by/delete_reason`), mesma
tabela de retenção por tenant (`companies.
outsourced_company_retention_years`, registrada em
`core.archival.RETENTION_COLUMNS`), mesma convenção de `action_type` de
auditoria (`outsourced_company_archived/restored/purge_requested/
purge_cancelled/purged`).

**Achado importante**: `outsourced_companies.status` já existia como um
campo de texto livre PT-BR (`'Ativa'`/`'Inativa'`), gravável pelo
formulário de criar/editar, mas nunca lido por nenhuma tela/filtro. Ele é
redefinido para ser o campo de lifecycle (mesmo contrato de `employees`/
`units`), com backfill de qualquer valor fora do novo enum
(`active/inactive/archived/pending_deletion/deleted`) para `'active'`
antes de aplicar o `CHECK` constraint no Postgres. O formulário de criar/
editar empresa deixa de aceitar `status` do payload do cliente — o
lifecycle passa a ser gerido exclusivamente pelas rotas de arquivar/
restaurar/expurgar.

Colaboradores terceirizados/prestadores **já são arquiváveis hoje, sem
nenhuma alteração** — são linhas comuns de `employees`, e o motor
genérico de arquivamento já opera sobre `employees.id` sem se importar
com `tipo_vinculo`. O trabalho novo aqui é só de exposição na nova aba
"Colaboradores Arquivados" (filtro sobre `fetch_archived_employees`, sem
rota nova) e uma checagem adicional: arquivar a empresa terceirizada
bloqueia (com aviso, não bloqueio silencioso) o cadastro de novos
colaboradores contra ela e novas entregas para colaboradores já
vinculados a ela, via `core.archival.ensure_record_operational`.

### 10.5 "Cadastros Pendentes"

Reaproveita o campo já existente `outsourced_companies.registration_status
== 'pending_completion'` (empresa em modo Simplificado, sem CNPJ ainda) —
sem tabela nova, sem estado novo. Não existe conceito equivalente para
colaboradores: o formulário simplificado já exige todos os campos
obrigatórios na criação, então não há colaborador "incompleto" a
rastrear — só a empresa pode nascer incompleta (CNPJ pendente).

### 10.6 Plano de implementação — PRs 10-15 (implementado)

1. **PR 10 — Fundação.** Novo módulo `terceirizados_colaboradores` em
   `MODULE_KEYS`/`MODULE_REQUIRED_PERMISSIONS` (piso técnico
   `employees:create_simplified`), permissões
   `employees:create_simplified`/`employees:update_simplified` concedidas a
   `admin`/`user` e listadas em `MASTER_ADMIN_OPERATIONAL_EXCLUSIONS` (mesma
   regra que já excluía `employees:create`/`update` do `master_admin`),
   chave `module_unit_scope: {module: [unit_id, ...]}` no mesmo
   `configuration_framework` que já guarda `module_visibility`, e a terceira
   condição em `resolve_module_visibility()` descrita no §10.3. Corrigido,
   nesta mesma leva, um import cíclico sinalizado pelo CodeQL entre
   `modules/settings` e `modules/employees`. Zero mudança de comportamento
   visível até alguém configurar `module_unit_scope` para um módulo
   existente.
2. **PR 11 — Rota do Cadastro de Colaboradores simplificado.**
   `POST/PUT /api/employees/outsourced-simplified(/{id})`, piso
   `employees:create_simplified`/`update_simplified`, delegando para as
   mesmas `create_employee`/`update_employee` do §10.1 — sem caminho de
   gravação paralelo. Validação dedicada
   (`validate_employee_outsourced_simplified_payload`) recusa CLT e exige
   `outsourced_company_id`, mantendo o formulário completo (`employees:
   create`) inalterado para quem já o usa.
3. **PR 12 — Arquivamento de `outsourced_companies`.**
   `POST /api/outsourced-companies/{id}/archive` e `.../restore` sobre o
   motor genérico `core/archival.py` (§10.4); redefinição de
   `outsourced_companies.status` de texto livre para o enum de lifecycle
   compartilhado, com backfill antes do `CHECK` constraint.
4. **PR 13 — Colaboradores Arquivados + relatório de headcount.** Filtro
   `outsourced_only=1` em `GET /api/employees/archived` (reaproveita
   `fetch_archived_employees`, sem rota nova);
   `GET /api/outsourced-companies/employees-summary` para o headcount por
   empresa; `core.archival.ensure_record_operational` passa a bloquear (com
   aviso) novo cadastro/entrega contra empresa arquivada, conforme §10.4.
5. **PR 14 — Flutter.** `OutsourcedCompaniesScreen` ganha abas
   Empresas/Colaboradores/Empresas Arquivadas/Colaboradores Arquivados/
   Relatórios; API client e cubits para arquivar/restaurar/relatório;
   roteamento e menu corrigidos para aceitar `employees:create` OU
   `employees:create_simplified` **e** o módulo `terceirizados` OU
   `terceirizados_colaboradores` (`routePermissionAlternatives`/
   `routeModuleAlternatives`) — sem essa correção `admin`/`user`, que só têm
   a versão simplificada, nunca alcançavam a tela mesmo com o módulo
   habilitado. Card de administração de `module_unit_scope` na tela de
   Configurações, irmão do card de `module_visibility` já existente.
6. **PR 15 — Web Legado.** Mesma paridade de funcionalidades do PR 14 na
   tela `#terceirizados-view` (`static/`): aba "Cadastro de Colaboradores",
   abas de arquivamento com filtros, aba de relatórios, e a mesma correção
   de escopo de acesso (`VIEW_PERMISSION_ALTERNATIVES`/
   `VIEW_MODULE_ALTERNATIVES` consumidos em `canAccessView()`). Listagem de
   colaboradores terceirizados derivada client-side de `state.employees`
   (já carregado pelo bootstrap) — sem rota de listagem nova, mesma
   estratégia do Flutter. Sistema genérico `ARCHIVAL_ENTITIES` estendido com
   `supportsPurge`/`identityKind`/`archivedQueryExtra` para cobrir empresas
   (sem expurgo) e colaboradores (listagem filtrada) sem duplicar código do
   arquivamento já existente de `employees`/`epis`.

Critério de aceite em cada PR desta extensão: suíte completa (`pytest`,
`flutter analyze`/`test`, runner JS `static/js/test/run-tests.js`) verde,
mais teste manual em navegador antes de qualquer PR de UI ir para revisão —
mesmo critério do §7.

## 11. Extensão — CRUD de empresas terceirizadas descentralizado por Unidade

Até aqui, `module_visibility`/`module_unit_scope` (§10.3) só controlavam se
Administrador Local/Gestor de EPI **enxergavam** o módulo — a rota de
escrita de `outsourced_companies` continuava exigindo `employees:create`/
`employees:update` completos, que esses dois papéis nunca têm (decisão do
§10.2). Resultado: mesmo com o módulo ligado para a unidade, esses perfis
não conseguiam de fato cadastrar/editar/arquivar/reativar empresas
terceirizadas — só o Cadastro de Colaboradores (§10.1) já funcionava de
ponta a ponta. Esta extensão fecha essa lacuna, mantendo a mesma condição
vinculante das extensões anteriores: **reaproveitar o mecanismo já
existente de visibilidade/permissão por perfil e unidade, sem criar um
novo mecanismo de autorização.**

### 11.1 Piso técnico ampliado com OR, não substituído

`MODULE_REQUIRED_PERMISSIONS['terceirizados']` passa de
`{employees:create}` para `{employees:create, employees:create_simplified}`
— basta UMA das duas (semântica OR, igual a
`routePermissionAlternatives` no Flutter e `VIEW_PERMISSION_ALTERNATIVES`
no Web Legado). Isso não amplia o que `admin`/`user` já podiam fazer em
qualquer outro módulo: eles só ganham `employees:create_simplified` desde
o §10.2, e essa permissão já era deles. O que muda é que agora ela também
abre a rota de CRUD de `outsourced_companies`, não só o Cadastro de
Colaboradores. Novo helper `core.repository.authorize_action_any(
connection, actor_user_id, actions, company_id=None)` tenta cada permissão
da lista e sucede na primeira que bater — usado nas rotas de
`outsourced_companies` e nas de arquivamento de colaborador terceirizado
(§11.4). Mantido fora de `core/auth.py`/`core/permissions.py`/
qualquer módulo referenciado pelo teste estrutural
`test_module_visibility_is_not_referenced_by_real_authorization_code` —
ele não referencia `module_visibility`, só resolve permissão.

### 11.2 `ensure_module_enabled_for_unit` como autoridade real de escrita

`modules.settings.service.ensure_module_enabled_for_unit(connection, actor,
module, unit_id)` já existia (§10.3, usado pelo Cadastro de Colaboradores)
e é exatamente o gate que faltava nas rotas de `outsourced_companies`:
levanta `PermissionError` a menos que o módulo esteja habilitado para a
unidade do ator (ou o ator não seja escopado por unidade). Passa a ser
chamado em `POST/PUT /api/outsourced-companies` e em
`archive/restore/delete`, sempre com o módulo `'terceirizados'` e a
unidade resolvida da empresa (ver §11.3). Nenhuma rota nova de
autorização — a mesma função, os mesmos dados de configuração que o
Administrador Geral já edita em Configuração → Regras → Visualização.

### 11.3 Escopo por Unidade na própria empresa terceirizada

Nova coluna `outsourced_companies.unit_id` (nullable — `NULL` = "do
tenant", sem Unidade, comportamento anterior a esta extensão preservado
para quem não usa o recurso). `resolve_outsourced_company_unit_id(
connection, actor, payload, company_id)` decide o valor: para
`admin`/`user` é **sempre** a unidade operacional do ator
(`actor_operational_unit_id`, o mesmo resolvedor de `employees`/entregas/
fichas) — o valor enviado no payload é ignorado, igual ao padrão já
estabelecido em `modules.employees.service.
ensure_actor_unit_scope_for_target`; para os demais perfis, o payload pode
informar uma unidade (validada contra a mesma empresa/tenant) ou omitir
(empresa "do tenant"). `ensure_actor_outsourced_company_scope` bloqueia
`admin`/`user` de ler, editar ou arquivar/reativar uma empresa que não
seja da própria unidade — inclusive empresas "do tenant" (`unit_id IS
NULL`), que ficam visíveis só para quem não é escopado por unidade.
`fetch_outsourced_companies`/`fetch_archived_outsourced_companies`/
`fetch_outsourced_employees_summary` recebem o mesmo filtro por unidade
quando chamadas por `admin`/`user`. Promoção a Cadastro Padrão
(`promote_outsourced_company`) e criação avulsa de Ordem de Serviço
(`POST /service-contracts`) permanecem **fora** desta extensão — seguem
exigindo `employees:update` completo (Administrador Geral/de Registro),
por decisão explícita: descentralizar cadastro e ciclo de vida básico não
significa descentralizar a promoção formal ao Cadastro Padrão.

### 11.4 Lacuna colateral corrigida: arquivar/reativar Colaborador Terceirizado

Ao implementar o item acima ficou evidente uma segunda lacuna, dentro do
escopo do mesmo pedido ("arquivar e reativar colaboradores terceirizados"):
o Cadastro de Colaboradores simplificado (§10.1) já permitia criar/editar,
mas as rotas de arquivar/reativar/excluir colaborador
(`DELETE/POST .../archive/.../restore /api/employees/{id}`) continuavam
exigindo `employees:delete`/`employees:update` completos — `admin`/`user`
nunca tinham essas permissões, então um colaborador terceirizado criado
por eles não podia ser arquivado por eles. Corrigido do mesmo jeito: essas
três rotas aceitam agora `employees:update_simplified` como alternativa
(via `authorize_action_any`), mas SÓ quando o colaborador-alvo é de fato
terceirizado/prestador (`tipo_vinculo != 'CLT' AND outsourced_company_id`)
— um colaborador CLT nunca pode ser arquivado por essa permissão estreita,
preservando o limite do §10.2. Após essa checagem,
`ensure_actor_employee_scope` (já existente) e
`ensure_module_enabled_for_unit(connection, actor,
'terceirizados_colaboradores', ...)` aplicam o mesmo par
escopo-de-unidade + módulo-habilitado do restante desta extensão.

### 11.5 Auditoria e relatórios — sem mudança de contrato

Toda gravação já passava por `record_audit_log`/`action_type` existentes
(`outsourced_company_created/updated/archived/restored`,
`employee_archived/restored`) — nenhuma tabela de auditoria nova. O
`unit_id` (quando presente) entra nos `details`/`changes` do log de
auditoria já existente. Relatórios de terceirizados/prestadores/
colaboradores (§10.4, headcount por empresa) já filtravam por
`company_id`; ganham o mesmo filtro por `unit_id` que as rotas de leitura
(§11.3) — sem rota de relatório nova.

### 11.6 Frontend — Web Legado e Flutter

Web Legado (`static/`): `hasPermission()` passa a aceitar lista/string
com múltiplas permissões alternativas (`normalizePermissionList`), usada
no envio do formulário de empresa e no `data-update-permission` de
`outsourced-company-form`; `ARCHIVAL_ENTITIES.outsourcedCompany`/
`outsourcedEmployee` ganham a mesma alternativa `employees:update_simplified`;
`renderArchivedRecords` amplia a lista de papéis que podem
arquivar/restaurar para incluir `admin`/`user` nesses dois tipos.
Formulário de empresa ganha um seletor de Unidade (`outsourced-company-
unit`), populado como qualquer outro seletor de Unidade já existente
(`outsourced-employee-unit`) — sem restrição client-side por papel, porque
`resolve_outsourced_company_unit_id` (§11.3) já força `admin`/`user` à
própria unidade no backend independente do que o formulário envie.

Flutter (`epi_admin`): mesmo ajuste de piso alternativo na visibilidade da
aba "Empresas" dentro de `OutsourcedCompaniesScreen`
(`employees:create` OU `employees:create_simplified`, já que o roteamento
para a tela como um todo já aceitava as duas desde o PR 14 — a lacuna era
só dentro da própria tela); `OutsourcedCompany.unitId` novo no modelo
(`epi_api`), com seletor de Unidade no formulário de criar/editar,
carregado via `ApiClient.auth.bootstrap()` no mesmo padrão do formulário
de Colaborador Terceirizado. Nenhuma tela nova, nenhuma rota de API
cliente nova além do campo `unit_id` no corpo já existente de
POST/PUT `/api/outsourced-companies`.

## 12. Extensão — Compartilhamento do cadastro corporativo por tenant + trava pós-promoção

O §11 resolveu a descentralização do CRUD, mas manteve `outsourced_
companies.unit_id` como fronteira de **visibilidade**: cada empresa
terceirizada pertencia a exatamente uma Unidade (ou a nenhuma, "do
tenant"), e uma Unidade que contratasse a mesma empresa terceirizada que
outra Unidade já usava (mesmo CNPJ) não tinha como enxergá-la — só
cadastrar de novo, duplicando o registro corporativo e fragmentando
histórico/auditoria/ressarcimento do mesmo CNPJ em duas linhas
independentes. Esta extensão corrige isso: o cadastro corporativo passa a
ser único por tenant (por CNPJ, como sempre foi a intenção do §3), e cada
Unidade que precisa usá-lo cria o próprio **vínculo operacional**, sem
depender de qual Unidade cadastrou primeiro.

### 12.1 `unit_id` vira metadado histórico imutável

`outsourced_companies.unit_id` deixa de ser lido/escrito em qualquer
`UPDATE` — `update_outsourced_company` não aceita mais o parâmetro
`unit_id` (removido da assinatura; o payload nunca é consultado para esse
campo). Continua gravado uma única vez, na criação
(`resolve_outsourced_company_unit_id`, inalterado desde o §11.3), como
"Unidade de origem": só metadado histórico de quem cadastrou primeiro,
nunca mais a fronteira de quem pode usar o registro. Nenhuma migração de
dado é necessária — o valor já gravado simplesmente passa a significar
"origem", não "dono exclusivo".

### 12.2 `outsourced_company_unit_links` — vínculo operacional por Unidade

Tabela nova (`core.schema.ensure_outsourced_company_unit_links`,
`supabase/migrations/20260806000000_outsourced_company_unit_links.sql`,
migration Postgres `021_outsourced_company_unit_links`): liga uma
`outsourced_company_id` a uma `unit_id`, com `local_status`
(`active`/`inactive`), motivo de desativação e auditoria de quem
criou/alterou. `create_outsourced_company` (service.py) já cria o vínculo
da própria Unidade de origem automaticamente ao cadastrar — nenhum passo
extra para o fluxo já existente. Uma Unidade *diferente* da origem cria o
vínculo explicitamente com a ação "Vincular à minha unidade"
(`POST /api/outsourced-companies/{id}/link`,
`create_outsourced_company_unit_link`) — idempotente: vincular de novo
reaproveita o vínculo existente em vez de duplicar (`UNIQUE (company_id,
outsourced_company_id, unit_id)`).

### 12.3 Descoberta: lista dividida + busca

`fetch_outsourced_companies` (service.py) devolve `{'linked': [...],
'available': [...]}` em vez de uma lista só — mudança de contrato
deliberada, refletida em `GET /api/outsourced-companies` como
`outsourced_companies`/`items` (linked) + `available_outsourced_companies`
(available). `linked` = empresas com vínculo ativo para a Unidade do ator
(via `outsourced_company_unit_links`) — dados completos, iguais a antes.
`available` = as demais empresas do tenant que a Unidade ainda não
vinculou — só campos públicos, via `_mask_outsourced_company_public_fields`
(CNPJ mascarado tipo `11.***.***/****-81`, sem contrato/nota/observação
interna). Para quem não é escopado por Unidade (general_admin/
registry_admin/master_admin), `linked` continua sendo TODAS as empresas do
tenant e `available` fica sempre vazio — comportamento inalterado desde
antes desta extensão. `GET /api/outsourced-companies/search?q=` (
`search_outsourced_companies_by_name`) permite localizar uma empresa já
cadastrada por outra Unidade antes de cadastrar de novo, com a mesma regra
de mascaramento (`annotate_outsourced_company_visibility`, reaproveitada
entre a lista principal e a busca).

### 12.4 Duplicidade de CNPJ vira "encontrada, vincule" em vez de bloqueio surdo

Antes desta extensão, tentar cadastrar um CNPJ já usado por outra Unidade
do mesmo tenant caía no `UNIQUE (company_id, cnpj_normalized)` como erro
genérico de banco. `validate_outsourced_company_payload` agora detecta a
duplicata ANTES do `INSERT` e levanta `DuplicateOutsourcedCompanyError`
(com `existing_company_id`), traduzida pela rota em
`409 {"error": <mensagem>, "code": "duplicate_cnpj", "existing_company_id":
<id>}`. O frontend (`handleOutsourcedCompanyDuplicateError`, app.js)
oferece vincular à empresa já existente em vez de insistir no cadastro.
Sem CNPJ (Cadastro Simplificado), a mesma checagem não é possível por
identidade exata — `POST /api/outsourced-companies` faz uma busca por nome
antes de criar e devolve `409 {"code": "possible_duplicate", "matches":
[...]}` quando encontra parecidos; o operador confirma explicitamente
(`confirm_duplicate: true` no payload) para seguir cadastrando mesmo assim,
sem travar o caso legítimo de duas empresas com nome parecido e CNPJ
diferente.

### 12.5 Trava pós-promoção — edição corporativa exclusiva de Geral/Registro

Enquanto a empresa está no Cadastro Simplificado (`registration_mode ==
'simplified'`), qualquer Unidade vinculada continua editando/arquivando
normalmente (mesma regra do §11.3). A partir da promoção ao Cadastro
Padrão (`registration_mode == 'standard'`, §2), os dados corporativos
(razão social, CNPJ, tipo, responsabilidade pelo EPI) passam a exigir
`employees:update` completo — `ensure_actor_can_edit_outsourced_company_
corporate_fields(actor, entity)` é a nova checagem, chamada em
`PUT /api/outsourced-companies/{id}` e em archive/restore/delete, sempre
**depois** de `ensure_actor_outsourced_company_scope` (a checagem de
vínculo continua valendo primeiro — sem vínculo, nem chega a saber se está
travado). Master fica de fora da exceção por doutrina já documentada
(`PAPEIS_E_ATRIBUICOES.md` #1: Master é operacional/suporte, nunca
substitui Geral/Registro em decisão de dado corporativo). Motivo da trava:
uma vez que o cadastro é "de verdade" (Padrão, usado por potencialmente
várias Unidades), uma edição feita por uma Unidade não deveria mudar dado
que outras Unidades também dependem sem revisão central.

Administrador Local/Gestor de EPI que precisa de uma correção usa
"Solicitar atualização cadastral" (`POST /api/outsourced-companies/{id}/
update-requests`, tabela nova `outsourced_company_update_requests`) — um
pedido em texto livre, nunca uma edição automática. Administrador Geral/de
Registro resolve pela aba "Solicitações"
(`GET .../update-requests`, `POST .../update-requests/{id}/resolve`),
que só aparece para quem tem `employees:update` completo
(`syncViewTabsVisibility` esconde a aba quando o card correspondente fica
`hidden`, mesmo mecanismo genérico de abas do resto do Web Legado — nenhum
código de visibilidade novo). Modelo deliberadamente enxuto (pedido +
resolução), não uma máquina de estados de aprovação em várias etapas.

### 12.6 Vínculo local nunca é arquivamento corporativo

Ativar/desativar o vínculo de uma Unidade (`POST .../unit-link/activate`
`.../unit-link/deactivate`, `set_outsourced_company_unit_link_status`)
muda só `outsourced_company_unit_links.local_status` daquela Unidade —
nunca `outsourced_companies.status`. Uma Unidade que encerrou o contrato
com a terceirizada desativa o próprio vínculo (com motivo opcional) sem
afetar as demais Unidades que ainda a usam, nem exigir arquivar o cadastro
corporativo (que só faz sentido quando NENHUMA Unidade mais usa a
empresa — decisão operacional de cada Unidade, fora do escopo automático
desta extensão). Liberado para Administrador Local/Gestor de EPI
independente de `registration_mode` — a trava do §12.5 é só sobre dado
corporativo, o vínculo é sempre local.

### 12.7 Colaborador terceirizado: referência exige vínculo, não mais Unidade de origem

`validate_employee_outsourced_reference` (chamada por
`modules.employees.service.create_employee`/`update_employee`) trocou a
checagem "mesma Unidade de origem" por
`is_outsourced_company_available_to_unit(connection, entity, unit_id)`:
disponível quando a empresa é "do tenant" (`unit_id` de origem nulo —
mesmo comportamento de sempre) OU quando a Unidade do colaborador tem
vínculo ativo com ela. Um colaborador da Unidade B só pode referenciar uma
empresa que a Unidade B já vinculou — nunca herda automaticamente o
vínculo de outra Unidade. Mesma regra em `fetch_outsourced_employees_
summary` (relatório headcount por empresa, §11.5): Administrador Local/
Gestor de EPI só vê o resumo das empresas vinculadas à própria Unidade e,
dentro delas, só os PRÓPRIOS colaboradores (`employees.unit_id` igual à
Unidade do ator) — nunca o headcount de outra Unidade que também vinculou
a mesma empresa compartilhada.

### 12.8 Migração e backfill

`supabase/migrations/20260806000000_outsourced_company_unit_links.sql`
cria as duas tabelas com RLS habilitado desde a criação (`block_direct_
api_access`, mesma policy restritiva do resto do backend) e faz backfill:
toda empresa terceirizada já cadastrada com `unit_id` preenchido ganha o
vínculo ativo correspondente para essa Unidade — sem isso, registros
criados antes desta extensão apareceriam como "não vinculados" mesmo para
a própria Unidade que os cadastrou, depois do deploy. Idempotente (`IF NOT
EXISTS`/`NOT EXISTS`), reexecução segura.

### 12.9 Frontend — Web Legado

Aba "Lista" (`terceirizados.html`) ganha uma segunda seção, "Empresas
disponíveis para vinculação", com os campos mascarados e o botão "Vincular
à minha unidade"; a tabela principal ganha a coluna "Vínculo Local"
(ativo/inativo + botão ativar/desativar). Formulário de cadastro/edição
ganha um aviso (`outsourced-company-corporate-lock-banner`) e os campos
corporativos ficam `disabled` quando a trava do §12.5 se aplica ao ator
atual — mesma decisão que o backend já tomaria, só evitando o roundtrip de
erro. Campo "Unidade" renomeado para "Unidade de origem" e sempre
`disabled` ao editar um registro existente (imutável, §12.1) — livre
apenas no cadastro, mesma trava por perfil operacional já existente desde
o §11.6. Nova aba "Solicitações" (só visível para quem tem
`employees:update` completo, §12.5). Regras puras (`isCorporateLocked`,
`canEditCorporateFields`) vivem em `js/views/outsourced-companies-view.js`,
testadas no harness — mesmo padrão do restante do módulo.

## 13. Extensão — Reutilização de Colaborador entre Unidades, CNPJ opcional/obrigatório por estágio e arquivamento local (pessoa)

**Status desta seção: proposta em avaliação — nenhum código deste escopo foi
escrito. Implementação aguarda aprovação explícita da arquitetura descrita
aqui.**

### 13.1 Contexto — dois problemas reais, um padrão já testado

O §12 resolveu o compartilhamento do cadastro corporativo (a *empresa*
terceirizada) entre Unidades. Esta extensão pede o mesmo tratamento para a
*pessoa* (o colaborador terceirizado/prestador) e fecha uma lacuna de
Multi-CNPJ que ficou exposta pelo mesmo motivo — código genérico demais
sendo aplicado a um caso que não é o dele.

**Problema A — alerta de bloqueio de CNPJ em produção.**
`create_employee_outsourced_simplified` (`modules/employees/service.py:399-402`)
chama incondicionalmente
`resolve_employee_legal_entity_id(connection, company_id, payload.get('legal_entity_id'))`
(`modules/legal_entities/service.py:593-613`) sempre que
`legal_entities_ready(connection)` é verdadeiro. Essa função pergunta "a
qual CNPJ **do próprio tenant** (`legal_entities.company_id → companies.id`)
este colaborador pertence" e levanta
`ValueError('Informe o CNPJ ao qual este colaborador pertence (a empresa
possui mais de um CNPJ ativo).')` sempre que a empresa contratante tem mais
de um `legal_entities` ativo e o payload não informou um. A pergunta é
legítima para um colaborador CLT (`create_employee`/`update_employee`
compartilham o mesmo bloco de código, linhas 155-160 e 223-229) — faz
sentido perguntar em qual filial do PRÓPRIO tenant a carteira de trabalho
está registrada. Para um colaborador terceirizado/prestador a pergunta não
se aplica: ele é empregado juridicamente pela **empresa terceirizada**
(`outsourced_companies`, uma pessoa jurídica diferente, com seu próprio
`cnpj`, sem nenhuma relação com `legal_entities`), nunca por um CNPJ do
tenant. O formulário de Cadastro Simplificado nunca teve (nem deveria ter)
um campo `legal_entity_id` — por isso o `alert()` que apareceu em produção
não tinha como ser satisfeito pela tela: é um beco sem saída herdado de um
código pensado para outro fluxo.

**Problema B — sem caminho para reaproveitar a mesma pessoa em outra
Unidade.** `employees.unit_id` é hoje posse única — uma linha de
`employees` pertence a exatamente uma Unidade. Quando a mesma empresa
terceirizada já está vinculada a duas Unidades (§12.2) e a segunda Unidade
precisa alocar operacionalmente a MESMA pessoa real (um técnico que atende
dois contratos do mesmo prestador, por exemplo), o sistema hoje nem sequer
deixa duplicar o cadastro silenciosamente: `ensure_employee_identity_unique`
(`modules/employees/service.py:77-97`) verifica CPF por `company_id`
(tenant inteiro, não por Unidade) e levanta `ValueError('CPF do
colaborador já cadastrado nesta empresa.')`. A segunda Unidade fica travada
sem alternativa — exatamente o mesmo formato de beco sem saída que o §12.4
já resolveu para CNPJ de empresa ("encontrada, vincule" em vez de bloqueio
surdo), só que ainda não existe para pessoa.

Os dois problemas têm a mesma causa-raiz (lógica pensada para "um só dono"
sendo aplicada onde agora existe compartilhamento) e o §12 já validou, em
produção, o padrão de solução: cadastro único por tenant + tabela de
vínculo operacional por Unidade. Esta extensão aplica o mesmo padrão à
pessoa e, separadamente, remove a pergunta de CNPJ do tenant de um fluxo
onde ela nunca fez sentido.

### 13.2 Decisões consolidadas

Lista fechada pelo usuário, preservada aqui na íntegra para rastreabilidade
(cada item referenciado como D1-D22 no restante desta seção):

1. **D1.** Cadastro Simplificado: CNPJ da empresa terceirizada/prestadora pode permanecer opcional.
2. **D2.** Cadastro Padrão/promoção: CNPJ passa a ser obrigatório.
3. **D3.** Empresa sem CNPJ: colaborador pode ser vinculado por `outsourced_company_id`, sem exigir `legal_entity_id`.
4. **D4.** Empresa com um único CNPJ: associação automática.
5. **D5.** Empresa com múltiplos CNPJs: seleção obrigatória do CNPJ empregador do colaborador.
6. **D6.** Empresa terceirizada/prestadora deve ser cadastrada uma única vez dentro do tenant.
7. **D7.** Colaborador terceirizado/prestador deve ser cadastrado uma única vez dentro do tenant.
8. **D8.** Outras Unidades reutilizam o cadastro existente, criando apenas vínculo/alocação operacional local.
9. **D9.** Vincular uma empresa a uma nova Unidade não deve vincular automaticamente todos os colaboradores.
10. **D10.** Cada Unidade escolhe quais colaboradores daquela empresa irão atuar localmente.
11. **D11.** Arquivamento da empresa é local por Unidade.
12. **D12.** Desarquivamento da empresa também é local por Unidade.
13. **D13.** Arquivamento do colaborador é local por Unidade.
14. **D14.** Desarquivamento do colaborador também é local por Unidade.
15. **D15.** Arquivar em uma Unidade não pode afetar outra Unidade onde empresa ou colaborador estejam ativos.
16. **D16.** Empresa/colaborador arquivados localmente devem desaparecer dos seletores operacionais daquela Unidade.
17. **D17.** Desarquivamento deve restaurar o uso apenas naquela Unidade.
18. **D18.** Exclusão definitiva não é função do Gestor de EPI nem do Administrador Local.
19. **D19 (redação atualizada — aprovada pelo usuário).** A exclusão definitiva não pode ser executada por Administrador Local, Gestor de EPI ou outros perfis operacionais. A operação é restrita ao Administrador Geral dentro do seu tenant e ao Administrador Master dentro do seu escopo administrativo, sempre condicionada à política de retenção e às validações do sistema.
20. **D20.** Deve existir aviso antecipado quando registros estiverem próximos da data de elegibilidade para exclusão.
21. **D21.** Não excluir definitivamente se ainda existir vínculo ativo em outra Unidade.
22. **D22.** Preservar histórico, entregas de EPI, auditoria, contratos e registros obrigatórios conforme a política de retenção.

D6, D9, D11, D12, D15, D16, D17 já são exatamente o que o §12 entregou para
a *empresa* — nada muda nelas nesta extensão. D7, D8, D10, D13, D14 pedem o
equivalente para a *pessoa*. D18-D22 pedem que a exclusão definitiva
continue centralizada, reaproveitando um mecanismo que — como o §13.4
mostra — já existe quase inteiro. D1-D5 são especificamente sobre o CNPJ da
empresa terceirizada (não do tenant) e, como o §13.8 mostra, D1/D2 já estão
implementadas hoje.

**Status pós-revisão do usuário (rodada 2):** D4/D5 fechados na leitura
mínima (§13.8), D19 com redação atualizada acima (`general_admin` E
`master_admin` mantidos, comportamento já implementado — nada a mudar em
código), e a proposta de congelar `employees.unit_id` foi **rejeitada** em
favor de uma arquitetura que não toca esse campo (§13.11, agora informado
por um levantamento completo de uso do campo). Nenhuma pergunta em aberto
restante bloqueando o desenho — ver §13.17 para as confirmações finais.

### 13.3 Modelo de dados atual

**`employees`** (colunas relevantes a este escopo): `company_id`, `unit_id`
(posse única, não anulável na prática), `cpf`/`employee_id_code` (unicidade
verificada por `company_id` — `employee_id_code` por índice de banco
`uq_employees_company_employee_code`; CPF por checagem de aplicação em
`ensure_employee_identity_unique`, não por constraint), `outsourced_company_id`
e `service_contract_id` (nuláveis, `NULL` = colaborador CLT),
`legal_entity_id` (nulável, CNPJ **do tenant**, Multi-CNPJ — sem nenhuma
relação com `outsourced_companies.cnpj`). Além disso, `employees` já carrega
o conjunto completo de colunas de ciclo de vida genérico definido em
`core/archival.py` (`LIFECYCLE_COLUMNS`): `status`, `archived_at`,
`archived_by`, `archive_reason`, `retention_until`, `legal_hold`,
`legal_hold_reason`, `deleted_at`, `deleted_by`, `delete_reason`.

**`outsourced_companies`** (§3, §12): cadastro único por tenant desde o
§12.1 (`unit_id` = metadado histórico imutável de origem), `cnpj` nulável
(Cadastro Simplificado), `registration_mode` (`simplified`/`standard`),
mesmo conjunto de colunas de ciclo de vida do parágrafo anterior (migração
própria, `ensure_outsourced_company_archival_lifecycle_columns`, mesmo
formato de `core.archival.LIFECYCLE_COLUMNS` mas não a reaproveita
diretamente — duplicação já existente, anterior a esta extensão).

**`outsourced_company_unit_links`** (§12.2): o vínculo operacional por
Unidade já em produção — `id, company_id, outsourced_company_id, unit_id,
local_status ('active'|'inactive'), deactivated_at, deactivation_reason,
deactivated_by_user_id`, `UNIQUE(company_id, outsourced_company_id,
unit_id)`.

**`legal_entities`** (Multi-CNPJ, arquitetura irmã construída em paralelo
nesta mesma sessão, já mergeada): `company_id` (FK para `companies`, o
**tenant**, nunca para `outsourced_companies`), `cnpj`, `entity_type`
(`matriz`/`filial`/`subsidiaria`/`spe`/`jv_partner`/`consorciada`/`outro`),
`active`, `is_headquarters`, `parent_entity_id`. Existe para representar os
CNPJs **do próprio tenant**, não os de terceiros que prestam serviço a ele.

**`core/archival.py`**: ciclo de vida genérico (arquivar → desarquivar →
exclusão definitiva em duas etapas) já ligado a `units`/`employees`/`epis`/
`outsourced_companies`. Pontos relevantes: `MIN_RETENTION_YEARS = 5`,
retenção configurável por tenant e por entidade via `RETENTION_COLUMNS`
(já inclui `'employees': 'employee_retention_years'` e
`'outsourced_companies': 'outsourced_company_retention_years'`),
`ensure_purge_allowed` já bloqueia exclusão sob `legal_hold` ou dentro do
período de retenção, e já restringe a etapa de exclusão
(`request_purge`/`confirm_purge`) a `actor.get('role') in ('master_admin',
'general_admin')` (`_require_deletion_admin`, `modules/employees/routes.py:50-51`,
replicado em `modules/outsourced_companies/routes.py`). `archive_record`/
`restore_record` operam **sempre sobre a linha inteira** (`employees`/
`outsourced_companies`), nunca por Unidade — hoje isso é seguro para
`employees` só porque cada linha já pertence a uma única Unidade.

**O que não existe hoje:** nenhuma tabela equivalente a
`outsourced_company_unit_links` para pessoas. Confirmado por busca no
código (`employee_unit_link`, `employee_company_link` e variantes não
retornam nenhuma tabela) — é exatamente a peça que falta para D7/D8/D10/
D13/D14.

### 13.4 Estruturas reaproveitáveis

- **Forma de `outsourced_company_unit_links`** como molde direto de uma
  tabela nova `employee_unit_links` — mesmas colunas, mesmo papel
  (`local_status`, motivo/ator/data de desativação, `UNIQUE(company_id,
  employee_id, unit_id)` para a mesma proteção contra corrida entre
  Unidades vinculando a mesma pessoa quase ao mesmo tempo).
- **`core/archival.py` inteiro, sem alteração de contrato**, para D18-D22:
  a "política de retenção já existente" que o usuário pediu para reaproveitar
  é exatamente este módulo. `ensure_purge_allowed` só precisa ganhar UMA
  precondição nova (nenhum vínculo ativo em nenhuma Unidade — §13.5), não
  um mecanismo novo.
- **`resolve_employee_outsourced_unit_id`/`resolve_outsourced_company_unit_id`**
  (construídos nesta mesma sessão, §11): o padrão "o backend deriva o valor
  a partir do ator para perfis escopados e ignora o payload" é reaproveitado
  para a rota nova de criação de vínculo local do colaborador.
- **`is_outsourced_company_available_to_unit`** (§12.7) como molde de
  `is_employee_available_to_unit` — mesma forma: disponível quando "sem
  Unidade de origem" (não se aplica a pessoa, já que toda `employees` tem
  `unit_id`, ver §13.11) OU quando existe vínculo ativo para a Unidade do
  ator.
- **`annotate_outsourced_company_visibility` + lista dividida `linked`/
  `available` + `DuplicateOutsourcedCompanyError` → 409 "encontrada,
  vincule"** (§12.3/§12.4): molde direto do fluxo de busca+vínculo de
  colaborador. O gatilho já existe e já é testado: o `ValueError('CPF do
  colaborador já cadastrado nesta empresa.')` de
  `ensure_employee_identity_unique` (§13.1, Problema B) é hoje um erro
  surdo; passa a carregar o `id` do colaborador encontrado, do mesmo jeito
  que `DuplicateOutsourcedCompanyError` já faz para CNPJ.
- **`employees.outsourced_company_id`, `employees.cpf`,
  `employees.employee_id_code`** — inalterados; continuam sendo a
  identidade única da pessoa no tenant (D7).

### 13.5 Estruturas que não devem ser duplicadas

- **Não criar um segundo mecanismo de retenção/exclusão definitiva.** A
  exclusão continua acontecendo na linha `employees`/`outsourced_companies`
  inteira, nunca por Unidade — arquivar/desarquivar por Unidade
  (`employee_unit_links.local_status`) e excluir definitivamente
  (`core.archival`) são conceitos em camadas diferentes e não devem se
  fundir. A única mudança em `core/archival.py` é `ensure_purge_allowed`
  ganhar uma checagem de "nenhum `employee_unit_links`/
  `outsourced_company_unit_links` com `local_status='active'` em qualquer
  Unidade" antes de liberar a etapa 1 (D21) — sem tocar em
  `archive_record`/`restore_record`/`request_purge`/`confirm_purge`, que
  continuam corretos como estão.
- **Não duplicar `registration_mode`/promoção em `employees`.** Nenhuma das
  22 decisões pede um "Cadastro Simplificado/Padrão" para pessoa — D1/D2
  são sobre o CNPJ da empresa terceirizada, não sobre o colaborador.
- **Não duplicar a resolução de `legal_entity_id` para colaborador
  terceirizado.** O Multi-CNPJ (`legal_entities`) continua servindo
  exclusivamente colaborador CLT/nativo do tenant (§13.7) — nenhuma versão
  paralela dessa lógica nasce para o fluxo terceirizado.
- **Não criar um conceito de "empresa" para pessoa.** `employee_unit_links`
  liga `employee_id` + `unit_id`, ponto — `employees` continua sendo a
  única fonte de identidade da pessoa no tenant, sem duplicar nada que
  `outsourced_companies`/`outsourced_company_unit_links` já resolvem para
  empresa.

### 13.6 Relacionamento proposto pessoa/empresa/unidade

`companies` (tenant) é o topo de duas árvores independentes que hoje só se
tocam por acidente de código (§13.1, Problema A): a árvore de
`legal_entities` (CNPJs **próprios** do tenant, servindo `units` e
colaboradores **CLT**) e a árvore de `outsourced_companies` (CNPJs de
**terceiros**, servindo colaboradores **terceirizados/prestadores**). Um
colaborador terceirizado nunca deveria atravessar para a primeira árvore —
seu vínculo jurídico é com `outsourced_company_id`, não com
`legal_entity_id`.

Dentro da árvore de terceirização, a proposta é que `outsourced_companies`
e `employees` (quando `outsourced_company_id` não é nulo) sigam exatamente
o mesmo formato: um cadastro único no tenant (D6/D7), e uma tabela de
vínculo (`outsourced_company_unit_links`/`employee_unit_links`) que cada
Unidade povoa deliberadamente (D8/D9/D10). Vincular a empresa a uma nova
Unidade não pré-popula `employee_unit_links` para os colaboradores dessa
empresa — cada Unidade escolhe as pessoas, não herda a lista inteira
(D9/D10), inclusive porque a mesma empresa pode ter dezenas de
colaboradores e só alguns atendem cada contrato/Unidade específica.

### 13.7 Impacto no Multi-CNPJ — a correção do alerta de bloqueio (D3)

Correção proposta, mínima e isolada: `create_employee_outsourced_simplified`
e `update_employee_outsourced_simplified` (`modules/employees/service.py`)
param de importar/chamar `resolve_employee_legal_entity_id` e param de
incluir `legal_entity_id` nas colunas gravadas — pelo mesmo motivo que
`empresa_origem`/`outsourced_company_id` já ficam de fora do fluxo CLT,
`legal_entity_id` fica de fora do fluxo terceirizado. `employees.legal_entity_id`
permanece `NULL` para toda linha **nova** com `outsourced_company_id`
preenchido.

**Dado legado precisa de migração, não só a remoção da chamada (achado da
revisão Codex, §13.19).** `resolve_employee_legal_entity_id` já gravava um
`legal_entity_id` não nulo mesmo quando a empresa tinha só **um** CNPJ
ativo (o caminho de fallback `ensure_default_legal_entity`, que só é
evitado quando há mais de um — o alerta reportado só aparece no caso de
múltiplos, mas o vínculo indevido acontece em qualquer caso). Toda linha
`employees` com `outsourced_company_id` preenchido criada/editada antes
desta correção pode ter um `legal_entity_id` apontando para a matriz do
tenant — o que faz esse colaborador terceirizado aparecer indevidamente
como vinculado ao CNPJ do próprio tenant, e pode bloquear
`deactivate_legal_entity` (que recusa inativar CNPJ com colaborador ativo
vinculado) por causa de gente que nunca deveria ter sido contada ali. PR A
inclui uma migração adicional, aditiva e idempotente: `UPDATE employees SET
legal_entity_id = NULL WHERE outsourced_company_id IS NOT NULL AND
legal_entity_id IS NOT NULL` — mesmo padrão dual-track (SQLite +
Postgres/Supabase) das demais migrações desta sessão.

`create_employee`/`update_employee` (colaborador CLT) **não são tocados**
— continuam chamando `resolve_employee_legal_entity_id` exatamente como
hoje. Mesma disciplina de escopo já aplicada a `#175`/`#177` nesta sessão:
não refatorar código fora do problema relatado.

### 13.8 Impacto no Cadastro Simplificado/Padrão — CNPJ da empresa terceirizada (D1, D2, D4, D5)

**D1 e D2 já estão implementadas.** `validate_outsourced_company_payload`
(`modules/outsourced_companies/service.py:186-187`) já levanta
`ValueError('CNPJ é obrigatório para o Cadastro Padrão.')` quando
`registration_mode == 'standard'` e `cnpj` está vazio; `promote_outsourced_company`
(linhas 538-539) já bloqueia a promoção com
`ValueError('CNPJ é obrigatório para promover ao Cadastro Padrão.')` se
`cnpj` ainda não foi preenchido. Cadastro Simplificado já aceita `cnpj`
vazio (`outsourced_companies.cnpj TEXT NOT NULL DEFAULT ''`, índice único
parcial que ignora `cnpj_normalized = ''`). Nada a construir aqui — esta
seção apenas registra a confirmação.

**D3** é a mesma correção do §13.7, só reafirmada do ângulo da empresa:
quando a empresa terceirizada não tem CNPJ (Cadastro Simplificado),
`outsourced_company_id` já é suficiente para vincular o colaborador — não
existe (nem nunca existiu, de fato) uma exigência de `legal_entity_id` que
faça sentido aqui.

**D4/D5 — fechado pelo usuário: leitura mínima, sem Multi-CNPJ para
terceirizadas.** Não nasce tabela nova, não nasce conceito novo.
`outsourced_companies` continua sendo reaproveitada como está; o que muda é
a qualidade da busca/seleção no Cadastro de Colaborador:

- Continua existindo hoje mais de uma linha `outsourced_companies` com o
  mesmo `legal_name`/`trade_name` (CNPJs diferentes, ou ambas sem CNPJ — o
  índice único é por `cnpj_normalized`, não por nome) — isso não muda.
- Se a busca por nome encontra uma única `outsourced_companies`
  correspondente, seleciona automaticamente (D4 — já é o comportamento
  atual, nada a mudar).
- Se encontra mais de uma, a tela passa a exigir escolha explícita — em vez
  de pegar a primeira — mostrando informação suficiente para identificar a
  empresa correta (D5). Campos exibidos na desambiguação, por decisão do
  usuário:
  - Razão Social;
  - Nome Fantasia;
  - CNPJ, quando cadastrado (Cadastro Simplificado sem CNPJ continua
    permitido — D1 — e aparece como "CNPJ não informado", nunca bloqueia a
    escolha);
  - tipo da empresa (`company_kind`);
  - contrato, quando aplicável (`service_contracts.contract_ref`/
    `service_order_ref`, quando já existir um contrato ativo associado à
    `outsourced_companies` candidata).
- Nenhuma tabela de CNPJs de terceirizadas é criada nesta rodada. Se no
  futuro surgir necessidade funcional comprovada de uma terceirizada com
  múltiplos CNPJs formalmente agrupados sob um único cadastro, isso é
  escopo de ADR próprio — não desta extensão.

PR C (§13.15) implementa só isso: melhora a query/UI de busca de
`outsourced_companies` no Cadastro de Colaborador para retornar e exibir
esses campos, e passa a exigir seleção explícita quando há mais de um
resultado. Nenhuma mudança de schema.

### 13.9 Impacto no fluxo existente de entrega de EPI

**Não há novo fluxo de entrega.** O mecanismo de registro, baixa de
estoque e auditoria (`modules/deliveries/service.py`) permanece exatamente
o mesmo — nenhuma tabela nova, nenhuma tela nova, nenhum endpoint novo de
entrega. O único ponto de possível toque é uma condição de autorização já
existente, precisamente localizada:

```
modules/deliveries/service.py:114-117
employee_current_unit_id = get_employee_current_unit(connection, int(employee['id']))
requested_unit_id = int(payload.get('unit_id') or 0)
delivery_unit_id = int(requested_unit_id or employee_current_unit_id)
if int(employee_current_unit_id) != int(delivery_unit_id):
    raise ValueError(...)  # entrega só é aceita na Unidade ATUAL do colaborador
```

`employee_current_unit_id` vem de `get_employee_current_unit` — a mesma
função de movimentação descrita em §13.11 (retorna a Unidade da
movimentação temporária ativa hoje, senão `employees.unit_id`).

**Decisão final do usuário: este gate NÃO é ampliado.** A condição
permanece exatamente `delivery_unit_id == employee_current_unit_id`,
calculada exclusivamente por `get_employee_current_unit` — transferência
temporária ativa quando existir, senão `employees.unit_id`. `employee_unit_links`
**não** entra nessa conta, para não criar uma segunda fonte de verdade
para "Unidade operacional do colaborador". PR D (§13.15) não toca
`modules/deliveries/service.py` em nenhuma linha.

Consequência prática, explícita por decisão do usuário: um colaborador
terceirizado vinculado administrativamente à Unidade B
(`employee_unit_links` ativo) cuja Unidade operacional atual ainda seja A
**não pode receber EPI em B** até passar pelo fluxo já existente de
transferência temporária ou definitiva (`POST /api/employee-unit-movements`,
§13.11). O vínculo local resolve disponibilidade administrativa,
reutilização de cadastro entre Unidades e arquivamento/desarquivamento
local (D8/D10/D13-D17) — **não** resolve "onde a pessoa está fisicamente
hoje para fins de entrega", que continua sendo exclusivamente o sistema de
movimentação, intocado.

Releitura de D10 à luz desta decisão: "colaborador... pode ser utilizado no
fluxo de entrega daquela Unidade" passa a ser lido como "pode ser
selecionado/listado naquela Unidade, sujeito à mesma condição de entrega
que já existe" — não como uma autorização de entrega adicional. Nenhum
código de `modules/deliveries/` muda nesta extensão.

Como D7 mantém uma única linha `employees` por pessoa no tenant (nunca
duplicada entre Unidades), o histórico de entregas de um colaborador
compartilhado passa a ser **um único trilho**, de qualquer Unidade em que
ele tenha atuado — o oposto do risco atual, em que o beco sem saída do
Problema B (§13.1) levaria, na prática, a cadastros duplicados manuais e
histórico de entrega fragmentado em duas pessoas "diferentes" no sistema
caso alguém contornasse o bloqueio criando uma segunda pessoa com CPF
ligeiramente diferente digitado.

O snapshot histórico da entrega (§3.5, já registra Unidade/empresa no
momento da entrega) não muda de comportamento — uma entrega feita enquanto
o colaborador estava vinculado à Unidade A continua mostrando a Unidade A
mesmo que esse vínculo seja arquivado depois (D22, preservar histórico).

### 13.10 Impacto nos relatórios

**Correção (revisão Codex, §13.19): a frase original desta seção descrevia
`employees.unit_id` como "Unidade de origem, histórica" — inconsistente com
o próprio §13.11, que estabelece que o campo é a Unidade base/permanente,
**mutável** por transferência definitiva.** Corrigido abaixo.

`fetch_outsourced_employees_summary` (§11.5/§12.7) e qualquer relatório que
hoje filtra por `employees.unit_id` assumem implicitamente "1 linha = 1
Unidade". Com D7/D8, isso deixa de ser verdade: um relatório de headcount
por empresa/Unidade precisa decidir explicitamente entre três leituras, não
duas — `employees.unit_id` (Unidade base/permanente, mutável), a Unidade
atual efetiva (`get_employee_current_unit`, considera movimentação
temporária ativa) ou `JOIN employee_unit_links WHERE local_status =
'active'` (vínculos administrativos adicionais, potencialmente vários por
pessoa) — cada relatório precisa declarar qual das três responde à pergunta
que ele faz.

Exemplo concreto já identificado (não hipotético): `build_ficha_epi_html_by_period`
(`modules/ficha/service.py:538-543`) compara `employee['unit_id']` (bruto,
nem sequer a Unidade atual computada) contra a Unidade do ator e rejeita
qualquer diferença — um Administrador Local/Gestor de EPI da Unidade B
vinculado administrativamente a um colaborador cuja `unit_id` seja A
continua sem acesso à ficha por período dele, mesmo depois da ampliação de
`ensure_actor_employee_scope` (§13.13/§13.19). Entra explicitamente no
escopo de auditoria do PR D.

Não é possível enumerar exaustivamente todos os relatórios afetados nesta
ADR; a implementação (§13.15, PR D) precisa de um passo de auditoria
dedicado nesses call sites antes de considerar o trabalho completo — risco
registrado em §13.13.

### 13.11 Migração necessária

**Correção da rodada anterior:** a proposta original desta ADR (congelar
`employees.unit_id` como "Unidade de origem" imutável, por simetria com
`outsourced_companies.unit_id` do §12.1) foi **rejeitada pelo usuário** —
corretamente: `employees.unit_id` não é análogo ao campo de empresa. O
levantamento abaixo (mapa de uso completo, pedido explicitamente antes de
qualquer mudança de semântica) mostra por quê, e substitui a proposta
antiga por uma arquitetura que não toca o campo.

#### Mapa de uso de `employees.unit_id` (auditoria completa)

`employees.unit_id` já tem um significado preciso e ativo hoje —
**"Unidade base/permanente do colaborador"**, mutável ao longo do tempo —
e já convive com um sistema de transferência de dois modos,
`employee_unit_movements` (`movement_type`: `'temporary'` |
`'definitive'`):

1. **Único ponto de escrita direta**: `update_employee_unit(connection,
   employee_id, unit_id)` (`modules/employees/service.py:701-707`,
   `UPDATE employees SET unit_id = ?`). Comentário no próprio código:
   "Lotação operacional apenas. NUNCA altera `legal_entity_id`." Chamado
   por dois caminhos:
   - Diretamente na criação (`create_employee`/`create_employee_outsourced_simplified`)
     e na edição comum (`update_employee`/`update_employee_outsourced_simplified`,
     quando o payload muda `unit_id`).
   - Pela rota dedicada `POST /api/employee-unit-movements`
     (`handle_post_employee_unit_movements`,
     `modules/employees/routes.py:394-443`) quando `movement_type ==
     'definitive'` — a **"transferência permanente"** que o usuário citou.
     Grava também uma linha em `employee_unit_movements` (auditoria/
     histórico) e fecha qualquer movimentação temporária em andamento.
2. **"Transferência temporária"**: mesma rota, `movement_type ==
   'temporary'` — insere uma linha em `employee_unit_movements` com
   `source_unit_id`/`target_unit_id`/`start_date`/`end_date`, **sem tocar
   `employees.unit_id`**. É uma janela de data com início e fim.
3. **"Unidade atual" computada** (não é uma coluna, é derivada):
   `get_employee_current_unit(connection, employee_id)`
   (`modules/employees/service.py:505-524`) — se existe uma movimentação
   `temporary` com `start_date <= hoje <= end_date`, devolve o
   `target_unit_id` dela; senão devolve `employees.unit_id`.
   `apply_current_unit_allocation` faz a mesma coisa em lote (anota
   `current_unit_id`/`current_unit_name`/`unit_allocation_type` em listas
   de colaboradores).
4. **Consumidores da Unidade atual computada** (não do `unit_id` cru):
   - `ensure_actor_employee_scope` (`modules/employees/service.py:549-557`)
     — gate de autorização por item: Administrador Local/Gestor de EPI só
     age sobre colaborador cuja Unidade atual computada seja a própria.
   - Gate de entrega de EPI (`modules/deliveries/service.py:114-117`,
     detalhado em §13.9) — só aceita entrega na Unidade atual computada.
5. **Consumidor do `unit_id` cru, sem olhar movimentação**:
   `fetch_employees` (listagem, `PERM_EMPLOYEES_VIEW`) filtra só por
   `company_id` para todo papel não-`master_admin` — não filtra por
   Unidade na query; a Unidade atual é só anotada para exibição via
   `apply_current_unit_allocation`. Comportamento pré-existente, não
   tocado por esta extensão.
6. **Conclusão da auditoria**: não existe hoje uma separação entre
   "Unidade de origem" (histórica, imutável) e "Unidade atual" — existe
   **"Unidade base"** (`unit_id`, mutável via transferência definitiva) e
   **"Unidade atual efetiva"** (base, a menos que haja uma transferência
   temporária ativa). Não existe "vínculos adicionais por Unidade" —
   é exatamente essa peça que falta e que `employee_unit_links` adiciona,
   **como uma dimensão nova, não como substituição de nenhuma das duas
   acima**. Congelar `unit_id` quebraria a transferência definitiva
   (`update_employee_unit` deixaria de fazer sentido); o pedido do usuário
   de auditar antes de mexer estava certo — não mexer é a decisão correta.

#### Arquitetura aprovada (não toca `unit_id`/movimentações)

- **Identidade da pessoa**: `employees` continua sendo o único cadastro do
  colaborador terceirizado/prestador no tenant (D7) — inalterado por esta
  extensão.
- **Empresa empregadora/origem**: `employees.outsourced_company_id`
  continua vinculado à pessoa e não muda quando ela passa a atuar em outra
  Unidade — já é assim hoje (nenhum código toca esse campo fora do
  cadastro/edição explícitos), esta extensão não adiciona nem remove
  nenhuma regra aqui.
- **Disponibilidade por Unidade**: tabela nova `employee_unit_links` —
  `employee + unit + local_status`, mesmo par dual-track de todas as
  migrações desta sessão (SQLite via `core/schema.py`
  `ensure_employee_unit_links` + `core/bootstrap.py`; Postgres/Supabase via
  `epi_backend/migrations/0NN_employee_unit_links.py` +
  `supabase/migrations/*.sql` irmão, RLS desde a criação). Forma: `id,
  company_id, employee_id, unit_id, local_status ('active'|'inactive'),
  activated_at, activated_by_user_id, deactivated_at, deactivation_reason,
  deactivated_by_user_id, created_at, updated_at`, `UNIQUE(company_id,
  employee_id, unit_id)`. Essa relação, e só ela, determina disponibilidade/
  arquivamento/uso em entrega **por Unidade** (D13-D17); é uma dimensão
  **paralela e independente** de `unit_id`/`employee_unit_movements` — os
  dois sistemas respondem perguntas diferentes e não se cruzam: um diz
  "onde a pessoa está alocada/se deslocou" (existente, intocado), o outro
  diz "em quais Unidades ela está disponível para uso operacional
  terceirizado" (novo).
- **Backfill**: toda `employees` com `outsourced_company_id` preenchido
  ganha uma linha `employee_unit_links` ativa para a sua Unidade atual
  computada (`get_employee_current_unit` no momento do backfill, não o
  `unit_id` cru — para nascer consistente com o que o colaborador já
  reflete hoje) — idêntico em espírito ao backfill do §12.8, mesma
  exigência de idempotência. É um valor inicial, não uma sincronização
  contínua: depois do backfill, `employee_unit_links` só muda por ação
  explícita de vincular/arquivar/desarquivar — uma transferência definitiva
  subsequente **não** move automaticamente o vínculo local.
- **Transferências existentes**: `employee_unit_movements`,
  `update_employee_unit`, `get_employee_current_unit`,
  `apply_current_unit_allocation`, as rotas de
  `/api/employee-unit-movements` — **nenhuma linha alterada**. Nenhuma
  lógica nova concorre com esses fluxos (não-meta explícita, §13.16).
- **Gates que precisam de ampliação por OR** (não substituição — mesmo
  espírito do restante desta ADR): `ensure_actor_employee_scope` e,
  condicionalmente, o gate de entrega (§13.9) — ver risco em §13.13 e
  confirmação pedida em §13.17.
- **Correção de `create_employee_outsourced_simplified`/
  `update_employee_outsourced_simplified`** (§13.7) — mudança de código
  isolada, sem migração de schema associada, sem relação com
  `employee_unit_links`.
- **UX de desambiguação D4/D5** (§13.8) — sem migração de schema.

### 13.12 Rollback

Tabela nova e sem alteração de colunas existentes (aditiva, nulável onde
aplicável) — remover `employee_unit_links` e sua migração é reversível sem
perda de dado em `employees` (a tabela só guarda o vínculo derivado, nunca
identidade). A correção de `legal_entity_id` (§13.7) é reversão de função
única (reintroduzir as 4 linhas removidas) sem migração de dado envolvida
— não há necessidade de rollback de schema para desfazer essa parte
isoladamente. Backfill é idempotente (`IF NOT EXISTS`/`NOT EXISTS`) —
reaplicar depois de um rollback é seguro, mesmo padrão já documentado no
§12.8.

### 13.13 Riscos

- **Mascaramento de dado pessoal é mais sensível que mascaramento de CNPJ.**
  O molde do §12.3 (`annotate_outsourced_company_visibility`, lista
  "disponíveis" com campos públicos) expõe CNPJ mascarado de uma empresa —
  dado corporativo. Uma lista "colaboradores disponíveis para vincular"
  tenant-wide expõe potencialmente nome e CPF de uma **pessoa física**.
  Recomendo expor menos do que o equivalente de empresa expôs (nome e
  função, CPF mascarado ou omitido até o vínculo ser criado) — decisão de
  design explícita a confirmar, não herdar o padrão de empresa sem ajuste.
- **Relatórios não mapeados** (§13.10) — o levantamento de todos os pontos
  que leem `employees.unit_id` hoje só é confiável durante a implementação
  (grep dirigido + teste de regressão por relatório), não nesta ADR.
- **Corrida entre Unidades vinculando a mesma pessoa quase simultaneamente**
  — mesma proteção que `outsourced_company_unit_links` já usa
  (`UNIQUE(company_id, employee_id, unit_id)` + tratamento de conflito como
  "já vinculado", não erro).
- **Gates de escopo existentes não sabem de `employee_unit_links` e
  precisam de ampliação por OR, não substituição** (§13.11): pelo menos
  `ensure_actor_employee_scope` (`modules/employees/service.py:549-557`)
  compara contra a Unidade atual computada (`get_employee_current_unit`) e
  rejeita qualquer Unidade diferente — sem a ampliação, um Administrador
  Local/Gestor de EPI da Unidade B nunca vai conseguir abrir/editar um
  colaborador vinculado localmente a B cuja Unidade atual (base ou
  movimentação) seja A, mesmo depois do PR B. É trabalho real do PR D, não
  um detalhe.
- ~~**Gate de entrega de EPI...**~~ **Resolvido pelo usuário (§13.9):** o
  gate **não** é ampliado. `delivery_unit_id == employee_current_unit_id`
  continua sendo a única condição, exclusivamente via
  `get_employee_current_unit` (transferência temporária ativa, senão
  `employees.unit_id`) — `employee_unit_links` nunca entra nessa conta, por
  decisão explícita de não criar uma segunda fonte de verdade para Unidade
  operacional. `modules/deliveries/service.py` não é tocado por nenhum PR
  desta extensão.

### 13.14 Critérios de aceite

- Cadastrar um colaborador terceirizado/prestador via Cadastro Simplificado
  não levanta mais alerta de CNPJ do tenant, independentemente de quantos
  `legal_entities` ativos a empresa contratante tiver (corrige o bug de
  produção relatado; D3).
- `create_employee`/`update_employee` (colaborador CLT) continuam exigindo
  `legal_entity_id` exatamente como hoje — nenhuma regressão no fluxo
  Multi-CNPJ nativo (§13.7).
- CNPJ da empresa terceirizada continua opcional no Simplificado e
  obrigatório para promoção/Padrão (D1/D2 — já cobertos por teste
  existente; esta ADR não adiciona comportamento novo aqui).
- Uma segunda Unidade consegue localizar e vincular operacionalmente um
  colaborador terceirizado já cadastrado por outra Unidade (mesmo CPF), sem
  duplicar a linha `employees` e sem erro surdo (D6/D7/D8).
- Vincular uma empresa a uma nova Unidade não cria vínculo automático para
  nenhum colaborador dessa empresa — cada um precisa ser escolhido
  explicitamente (D9/D10).
- Arquivar um colaborador (ou empresa) em uma Unidade não altera sua
  visibilidade/uso em nenhuma outra Unidade onde o vínculo continue ativo
  (D11-D15).
- Colaborador/empresa arquivados localmente somem dos seletores
  operacionais daquela Unidade especificamente, e só daquela (D16/D17).
- Exclusão definitiva de colaborador/empresa continua restrita a
  `general_admin` (no próprio tenant) e `master_admin` (no seu escopo
  administrativo) — ninguém mais — e ao fluxo já existente em
  `core/archival.py`: registro arquivado, prazo de retenção cumprido,
  confirmação explícita em duas etapas, auditoria imutável; passa a também
  exigir inexistência de vínculo ativo em qualquer Unidade (D18/D19/D21).
- Existe aviso antecipado quando um registro se aproxima da data de
  elegibilidade para exclusão definitiva (D20).
- Histórico de entregas, auditoria, contratos e demais registros
  obrigatórios permanecem intactos e consultáveis após qualquer
  arquivamento local (D22).
- **Não regressão em transferência temporária**: criar uma movimentação
  `temporary` para um colaborador terceirizado continua funcionando
  exatamente como hoje (`employee_unit_movements`, `unit_id` da `employees`
  intocado, `get_employee_current_unit` reflete a Unidade de destino
  durante a janela de datas) — nenhum comportamento novo de
  `employee_unit_links` interfere.
- **Não regressão em transferência definitiva**: criar uma movimentação
  `definitive` continua atualizando `employees.unit_id` via
  `update_employee_unit` exatamente como hoje — `employee_unit_links` não
  muda automaticamente como efeito colateral dessa transferência (o vínculo
  local permanece o que foi explicitamente configurado até uma Unidade
  arquivar/desarquivar/vincular de novo).
- **Não regressão no cadastro CLT**: `create_employee`/`update_employee`
  (colaborador nativo do tenant, sem `outsourced_company_id`) não sofrem
  nenhuma mudança de comportamento — `employee_unit_links` só é populada
  para colaboradores com `outsourced_company_id` preenchido.
- Suíte de testes (backend + frontend, `pytest tests/ -q` e
  `node static/js/test/run-tests.js`) verde nos dois repositórios, incluindo
  testes novos para cada decisão D1-D22 tocada por código e para os três
  itens de não regressão acima.

### 13.15 Divisão sugerida em PRs

PR F (condicional, Multi-CNPJ para terceirizada) foi **removido**: D4/D5
fecharam na leitura mínima, sem tabela nova.

- **PR A — correção isolada do alerta de CNPJ (§13.7). Implementado,
  testado (32 testes, suíte completa 2178 verde) e enviado — não é mais
  proposta.** Removeu a chamada a `resolve_employee_legal_entity_id` do
  fluxo terceirizado simplificado + migração de limpeza para linhas
  legadas (`legal_entity_id = NULL WHERE outsourced_company_id IS NOT
  NULL`, achado da revisão Codex, §13.19).
- **PR B — `employee_unit_links`.** Schema + backfill (dual-track,
  semeando a Unidade base **e** a atual computada quando diferentes,
  cobrindo colaborador terceirizado legado sem `outsourced_company_id`, e
  **não** ativando vínculo para colaborador já arquivado globalmente —
  três ajustes do §13.19/§13.20) + `is_employee_available_to_unit` (exige
  vínculo ativo correspondente em `outsourced_company_unit_links` da mesma
  Unidade, §13.19) + rotas de vincular/ativar/desativar vínculo local +
  **criação do vínculo local inicial atomicamente com o colaborador, na
  própria Unidade que o cadastrou** (achado P1 do §13.20 — sem isso, todo
  colaborador cadastrado depois deste PR nasce indisponível até para quem
  o cadastrou) + testes, mesma forma do §12.2. Inclui os três testes de não
  regressão de transferência (§13.14) provando que `employee_unit_movements`/
  `update_employee_unit` continuam intocados. Não depende de nenhuma
  decisão em aberto.
- **PR C — busca + desambiguação no Cadastro de Colaborador (D4/D5).**
  Exibe Razão Social/Nome Fantasia/CNPJ (quando cadastrado)/tipo/contrato
  na busca de `outsourced_companies`; exige escolha explícita quando há
  mais de um resultado; fluxo "CPF já cadastrado → vincular" passa a exigir
  que o colaborador encontrado já seja terceirizado da mesma
  `outsourced_company_id` sendo escolhida (§13.19), caso contrário trata
  como conflito genuíno. Sem mudança de schema. Independente do PR B.
- **PR D — arquivar/desarquivar colaborador por Unidade + ampliação do
  gate de escopo administrativo por OR.** Depende do PR B. Frontend +
  backend para D13-D17; amplia `ensure_actor_employee_scope` por OR
  (Unidade atual **ou** `employee_unit_links` ativo, §13.13) — só esse
  gate administrativo, não o de entrega (decidido em §13.9: gate de
  entrega não muda por padrão nesta rodada — ver pergunta em aberto no
  §13.20 sobre uma precondição negativa específica de arquivamento).
  **Inclui as duas correções P1 do §13.19/§13.20**:
  `update_employee_outsourced_simplified` para de resolver/gravar `unit_id`
  **e** `outsourced_company_id` a partir do payload/ator — preserva
  `current['unit_id']`/`current['outsourced_company_id']`, só fluxos
  administrativos dedicados (transferência de Unidade, troca de fornecedor)
  mudam essas colunas — sem essa correção a ampliação do gate administrativo
  transferiria colaboradores e trocaria seu empregador silenciosamente.
  **Inclui também conectar `is_employee_available_to_unit` no endpoint real
  que alimenta os seletores de colaborador** (achado P1 do §13.20 — a
  função só existir não filtra nada sozinha). Auditoria dos relatórios
  afetados (§13.10), incluindo o gate de `build_ficha_epi_html_by_period`
  identificado nominalmente.
- **PR E — governança de exclusão definitiva.** `ensure_purge_allowed`
  ganha o parâmetro `connection` (não tinha, §13.19) para consultar
  ausência de vínculo ativo em qualquer Unidade (D21) — checagem chamada
  tanto em `request_purge` quanto em `confirm_purge` (não só na primeira
  etapa, §13.19; atomicidade dentro do `confirm_purge` fica como risco
  registrado, §13.20, não resolvida aqui) + aviso antecipado de
  elegibilidade (D20) + redação atualizada de D19 refletida em mensagens de
  erro/auditoria. **Escopo maior do que a rodada anterior previa (achado
  P1 do §13.20): `outsourced_companies` não tem hoje nenhuma rota de
  exclusão definitiva em duas etapas — PR E constrói `request`/`cancel`/
  `confirm`/resumo de histórico para `outsourced_companies`, no mesmo
  padrão já usado em `modules/employees/routes.py`, não só ajusta uma
  precondição compartilhada que já existia.** Depende do PR B já estar
  mergeado. Nenhuma mudança no gate `master_admin`/`general_admin` em si
  (já correto).

### 13.16 Não-metas desta rodada

- **Consolidação retroativa** de colaboradores que já foram cadastrados
  duas vezes (uma por Unidade) por não terem tido, até aqui, como se
  vincular — mesma decisão já registrada em §12 para empresa duplicada, e
  pela mesma razão: é uma operação de migração de dado mais pesada
  (merge de duas linhas `employees` + repointing de entregas/auditoria),
  candidata a um pedido dedicado.
- **Qualquer mudança em `create_employee`/`update_employee`** (colaborador
  CLT/nativo do tenant) — o escopo inteiro desta extensão é o colaborador
  terceirizado/prestador; o fluxo Multi-CNPJ nativo permanece intocado.
- **Qualquer mudança no gate de `master_admin`** em `ensure_purge_allowed`/
  `_require_deletion_admin` — comportamento pré-existente e explicitamente
  mantido por decisão do usuário (D19 atualizado, §13.2); nada a mudar em
  código aqui.
- **Qualquer mudança em `employees.unit_id`, `update_employee_unit` ou
  `employee_unit_movements`** (transferência temporária/definitiva) —
  rejeitado explicitamente pelo usuário na revisão do ADR. `employee_unit_links`
  é uma estrutura paralela e independente; não substitui, não sincroniza
  com e não intercepta o fluxo de transferência existente (§13.11).
- **Multi-CNPJ para empresa terceirizada/prestadora** (leitura estrutural
  de D4/D5, descartada) — fica para um ADR próprio se e quando houver
  necessidade funcional comprovada (§13.8).

### 13.17 Confirmações solicitadas antes da implementação — todas fechadas

Resposta direta aos itens 3-7 pedidos antes do primeiro PR de código
(itens 1 e 2 são este próprio documento e a divisão de PRs do §13.15). As
duas perguntas em aberto da rodada anterior (gate de entrega e ordem de
PRs) foram respondidas pelo usuário — **nenhuma pendência restante**;
implementação liberada a partir do PR A.

**3. Estruturas reaproveitadas** (detalhe em §13.4): forma de
`outsourced_company_unit_links` (molde de `employee_unit_links`);
`core/archival.py` inteiro e sem alteração de contrato (só uma precondição
nova em `ensure_purge_allowed`); `resolve_employee_outsourced_unit_id`/
`resolve_outsourced_company_unit_id` (padrão de resolver Unidade a partir
do ator); `is_outsourced_company_available_to_unit` (molde de
`is_employee_available_to_unit`); `DuplicateOutsourcedCompanyError` → 409
"encontrada, vincule" (molde para o CPF duplicado); `employees.cpf`/
`employee_id_code`/`outsourced_company_id` (identidade, inalterados).

**4. Confirmo que não haverá segunda base de colaboradores.**
`employees` continua sendo o único cadastro por pessoa no tenant (D7).
`employee_unit_links` guarda só `employee_id + unit_id + local_status` —
uma linha de vínculo, nunca uma cópia de identidade, nome, CPF ou qualquer
outro dado pessoal. Duas Unidades vinculadas à mesma pessoa apontam para a
mesma linha `employees.id`.

**5. Confirmado: não haverá novo fluxo de entrega de EPI.** O mecanismo de
registro, estoque e auditoria de entrega (`modules/deliveries/service.py`)
não ganha tabela, tela ou endpoint novo — e, por decisão final do usuário
(§13.9), **nem a condição de autorização é tocada**: `delivery_unit_id ==
employee_current_unit_id` continua sendo calculada exclusivamente por
`get_employee_current_unit` (transferência temporária ativa, senão
`employees.unit_id`). `employee_unit_links` não entra nessa conta — não
haveria duas fontes de verdade para Unidade operacional. Um colaborador
vinculado administrativamente à Unidade B cuja Unidade operacional atual
ainda seja A não recebe EPI em B sem passar pela transferência já
existente. `modules/deliveries/` não é tocado por nenhum PR desta
extensão.

**6. Representação do vínculo local colaborador × Unidade.** Tabela nova
`employee_unit_links` (`id, company_id, employee_id, unit_id, local_status
('active'|'inactive'), activated_at, activated_by_user_id, deactivated_at,
deactivation_reason, deactivated_by_user_id, created_at, updated_at`,
`UNIQUE(company_id, employee_id, unit_id)`) — detalhe completo em §13.11.
**Paralela e independente** de `employees.unit_id`/`employee_unit_movements`:
não sincroniza, não é atualizada por transferência temporária ou
definitiva, não intercepta nenhuma rota existente de movimentação. Muda
somente por ação explícita de vincular/arquivar/desarquivar por Unidade.

**7. Testes de não regressão para transferências** (já incorporados como
critério de aceite em §13.14, resumo aqui):
- Transferência **temporária** de um colaborador terceirizado: cria linha
  em `employee_unit_movements` (`movement_type='temporary'`),
  `employees.unit_id` não muda, `get_employee_current_unit` passa a
  refletir a Unidade de destino só durante a janela `start_date`/`end_date`,
  volta à Unidade base depois — sem qualquer interferência de
  `employee_unit_links`.
- Transferência **definitiva**: `update_employee_unit` continua sendo o
  único caminho que altera `employees.unit_id`; a linha de auditoria em
  `employee_unit_movements` (`movement_type='definitive'`) continua sendo
  gravada; `employee_unit_links` permanece exatamente como estava antes da
  transferência (não é criada, alterada nem removida como efeito
  colateral).
- Colaborador **CLT** (sem `outsourced_company_id`): nenhum comportamento
  novo — `employee_unit_links` nunca é populada para ele, backfill não o
  toca, `create_employee`/`update_employee` não mudam uma linha.
- **Ambos os testes de transferência rodam antes e depois do PR B** (mesmo
  resultado) — a prova de que a tabela nova não interfere.

**Ordem de PRs — aprovada pelo usuário, condição resolvida em §13.22:**
A → B → (C e D, ambos dependentes de B, mas paralelos *entre si*) → E. A
condição que a aprovação original deixou em aberto ("C e D em paralelo,
condicionado a permanecerem realmente independentes depois do PR B") se
resolveu como **não** para C (precisa de `employee_unit_links` do PR B
para persistir o vínculo do fluxo "encontrada, vincule") — corrigido no
§13.22. PR A já implementado; PR B é o próximo passo de código.

### 13.18 Governança de CI — issue separada, fora deste escopo

`API Contract & Multi-Tenant Scope`, `Lint (ruff)` e `PostgreSQL Schema &
Multi-Tenant` são required checks com `paths:` filter — nunca reportam em
PR que não toca `epi_backend/**`/`modules/**`/`tests/**`/etc., deixando o
PR bloqueado indefinidamente mesmo sem nenhum problema real (constatado
nos próprios PRs #181/#846 deste ADR). Correção dessa governança de CI é
tratada em issue própria, deliberadamente fora do escopo desta extensão —
não misturar. Ver issue de rastreamento aberta para esse problema
especificamente.

### 13.19 Revisão automatizada (Codex) — achados incorporados

O bot de review do Codex analisou o design desta seção antes de qualquer
código existir — exatamente o ponto em que uma revisão custa menos. Três
das afirmações mais centrais foram verificadas diretamente contra o código
antes de aceitar: `ensure_purge_allowed(record, actor, entity_label)`
(`core/archival.py:228`) de fato não recebe `connection`;
`build_ficha_epi_html_by_period` (`modules/ficha/service.py:538-543`) de
fato compara `employee['unit_id']` bruto contra a Unidade do ator;
`create_employee` (`modules/employees/service.py:100-130`) de fato permite
`tipo_vinculo != 'CLT'` com só `empresa_origem` livre, sem
`outsourced_company_id`. As três confirmadas — o restante dos achados
abaixo tem o mesmo nível de precisão e foi aceito com a mesma confiança.

**Achado mais importante (P1) — corrige um erro de design real antes que
vire código.** A ampliação por OR de `ensure_actor_employee_scope`
(proposta em §13.13/§13.15, PR D) autoriza um Administrador Local/Gestor de
EPI da Unidade B a agir sobre um colaborador vinculado localmente a B cuja
Unidade base ainda seja A. Mas `update_employee_outsourced_simplified`
(`modules/employees/service.py:434-480`) resolve `unit_id` a partir do
**ator** (`resolve_employee_outsourced_unit_id`) e grava
incondicionalmente essa Unidade em **toda** edição — inclusive uma edição
que só muda o nome. Combinados, os dois pontos significam que o primeiro
Administrador Local da Unidade B que editar qualquer campo desse
colaborador **transferiria silenciosamente sua Unidade base de A para B**,
sem passar pelo endpoint de transferência (`/api/employee-unit-movements`)
— exatamente o "criar lógica que concorra com os fluxos de transferência"
que a §13.16 lista como não-meta, só que como efeito colateral não
percebido, não como código escrito de propósito.

**Correção de design adotada para o PR D:** `update_employee_outsourced_simplified`
deixa de resolver/gravar `unit_id` a partir do payload/ator nesta edição —
preserva `current['unit_id']` inalterado, no mesmo padrão que
`legal_entity_id` já segue na edição comum ("um valor enviado no payload é
ignorado — a mudança só ocorre pelo processo administrativo auditado").
`unit_id` só muda por `POST /api/employee-unit-movements`, nunca por este
endpoint. A autorização da edição passa a depender só de
`ensure_actor_employee_scope` (já ampliado por OR) — não precisa mais
resolver um `unit_id`-alvo para autorizar, porque a edição não altera mais
essa coluna.

**Demais achados aceitos, com o ajuste correspondente:**

- **Backfill de `employee_unit_links` perde a Unidade base quando há
  movimentação temporária ativa no momento da migração.** `get_employee_current_unit`
  no momento do backfill devolve só a Unidade de destino da movimentação
  temporária; quando ela expirar naturalmente, a pessoa volta a
  `employees.unit_id`, mas sem vínculo lá (só no destino expirado). Ajuste:
  backfill semeia **as duas** Unidades quando forem diferentes — a base
  (`employees.unit_id`) e a atual computada — nunca só uma.
- **Critério do backfill/disponibilidade não cobre colaborador terceirizado
  legado sem `outsourced_company_id`.** `create_employee` sempre permitiu
  `tipo_vinculo` não-CLT com só `empresa_origem` livre, anterior ao
  `outsourced_companies` estruturado do ADR-0002. Backfill e toda lógica de
  disponibilidade baseada só em `outsourced_company_id IS NOT NULL`
  deixariam essas linhas legadas sem vínculo algum, somem dos seletores
  operacionais no rollout. Ajuste: critério do backfill passa a ser
  `outsourced_company_id IS NOT NULL OR tipo_vinculo <> 'CLT'`; linhas só
  com `empresa_origem` livre (sem `outsourced_company_id`) recebem vínculo
  igual, mas ficam de fora de qualquer validação que dependa de uma
  `outsourced_companies` real (não têm uma) — tratamento exato a refinar no
  PR B, registrado aqui como requisito, não como solução fechada.
- **`employee_unit_links` não exige vínculo ativo da própria empresa
  empregadora na mesma Unidade.** Nada impede hoje, no desenho original,
  vincular/reativar um colaborador numa Unidade onde
  `outsourced_company_unit_links` da sua `outsourced_company_id` esteja
  ausente ou arquivado — o colaborador ficaria operacional com o
  fornecedor indisponível ali, contradizendo D9/D16. Ajuste: criar/ativar
  `employee_unit_links` passa a exigir uma linha ativa correspondente em
  `outsourced_company_unit_links` para `(company_id, outsourced_company_id,
  unit_id)` — mesma Unidade, mesma checagem repetida nas consultas
  operacionais (`is_employee_available_to_unit`).
- **Fluxo "CPF já cadastrado → oferecer vincular" (§13.4) não valida que o
  registro encontrado é elegível.** Sem checar que o colaborador
  encontrado pelo CPF já é terceirizado **da mesma** `outsourced_company_id`
  sendo selecionada, o fluxo poderia oferecer reaproveitar um colaborador
  CLT ou de outro fornecedor. Ajuste: a resposta "encontrada, vincule" só é
  oferecida quando o colaborador encontrado tem `outsourced_company_id`
  preenchido **e** igual ao da empresa sendo escolhida na tela; qualquer
  outro caso (CLT, ou terceirizado de outro fornecedor) é tratado como
  conflito genuíno, sem oferta de vínculo automático.
- **`ensure_purge_allowed(record, actor, entity_label)` não recebe
  `connection`** — não tem como consultar as tabelas de vínculo para a
  precondição de D21 como proposto em §13.5. Ajuste: assinatura passa a
  receber `connection` (e os dados necessários para localizar vínculos),
  chamada tanto em `request_purge` quanto em `confirm_purge` — não só na
  primeira etapa, porque uma Unidade pode reativar um vínculo entre a
  solicitação e a confirmação do purge.
- **D6 (empresa cadastrada uma única vez) não está de fato garantido para
  o caso sem CNPJ**, mesmo após a melhoria de desambiguação de D4/D5: nada
  impede a criação de uma segunda `outsourced_companies` com nome parecido
  e `cnpj` vazio — a desambiguação ajuda a *encontrar e escolher* entre
  duplicatas depois de criadas, não *impede* a criação da segunda. Isto é
  mais precisamente um gap do §12 (que introduziu D6) do que desta
  extensão, mas fica registrado aqui: D6 continua parcialmente aberto para
  o caso sem CNPJ — prevenção de duplicidade nesse caso (busca+confirmação
  antes de criar, no padrão já desenhado no plano original desta sessão)
  não está confirmada como implementada e precisa de verificação
  independente, fora do escopo de código deste ADR.

**Achados aceitos como riscos reais, deliberadamente fora do escopo desta
extensão (não internalizados como trabalho do PR B-E):**

- **`employees.service_contract_id` é único por pessoa, não por vínculo.**
  Se o mesmo colaborador compartilhado atende a Unidade A sob um contrato e
  a Unidade B sob outro, o contrato/responsabilidade por EPI ficam presos
  ao que foi gravado por último — pré-existente ao sistema de movimentação
  (nem `update_employee_unit` toca `service_contract_id` hoje), mas esta
  extensão torna a situação de "mesma pessoa, Unidades diferentes" comum em
  vez de rara. Como o gate de entrega não é tocado (§13.9 — decisão do
  usuário), o pior caso prático é responsabilidade/contrato desatualizados
  no snapshot da entrega quando a pessoa é efetivamente transferida — não
  corrigido aqui; candidato a issue própria se e quando isso se mostrar um
  problema real em produção.
- **Unicidade de CPF é checagem de aplicação (SELECT-então-INSERT), não
  constraint de banco.** Duas Unidades submetendo o mesmo CPF novo quase
  simultaneamente podem, em tese, ambas passar `ensure_employee_identity_unique`
  e criar duas linhas `employees` para a mesma pessoa — pré-existente a
  esta extensão (a mesma corrida já existiria hoje entre duas criações
  quaisquer com o mesmo CPF), só que o D7/D8 aumenta o quanto isso importa
  na prática. Corrigir exigiria um índice único normalizado por
  `(company_id, cpf)` a nível de banco — mudança maior, com migração de
  dado preexistente potencialmente conflitante, fora do escopo deste ADR;
  registrado como risco a avaliar separadamente.

### 13.20 Revisão automatizada (Codex) — rodada 2

Segunda rodada, disparada pelo push do §13.19. Verifiquei diretamente os
dois achados mais consequentes antes de aceitar: não existe nenhuma rota
`request_purge`/`confirm_purge` para `outsourced_companies` hoje (só para
`employees`/`epis` — busca no repositório inteiro confirma) e
`modules/deliveries/service.py:68-123` de fato não consulta
`employee_unit_links` em nenhuma direção. As duas confirmadas.

**Achado que corrige um "dia 1" quebrado (P1).** Nada no desenho do PR B/C
faz `create_employee_outsourced_simplified` criar a linha inicial de
`employee_unit_links` para a própria Unidade que acabou de cadastrar o
colaborador. Como a disponibilidade passa a depender de vínculo ativo, todo
colaborador terceirizado cadastrado depois do deploy do PR B ficaria
indisponível até para quem acabou de cadastrá-lo. Ajuste: PR B/C cria o
vínculo local ativo atomicamente com o colaborador, na mesma transação —
mesmo padrão de qualquer operação criar+vincular já visto nesta ADR.

**Achado que expõe uma lacuna real de aplicação (P1).** A ADR propõe
`is_employee_available_to_unit` mas nunca especifica **onde** ele é
efetivamente consultado. Sem isso, os seletores que hoje consomem a lista
de colaboradores (bootstrap de `state.employees`, filtros por
`current_unit_id`/`unit_id` no Web Legado) continuam do jeito que estão
hoje — um colaborador vinculado a B mas com Unidade atual em A continua
ausente do seletor de B, e um colaborador desativado localmente em A
continua selecionável lá. Ajuste: PR D precisa **explicitamente** trocar
(ou envolver) o endpoint que alimenta esses seletores para aplicar
`is_employee_available_to_unit`, não só disponibilizar a função — mesmo
tipo de lacuna que o §13.19 já tinha identificado para
`ensure_actor_employee_scope`/ficha, agora encontrada também na listagem.

**Achado que corrige o escopo do PR E — mais fundo do que eu havia
desenhado (P1).** `outsourced_companies` **não tem hoje** nenhuma rota de
exclusão definitiva em duas etapas — `modules/outsourced_companies/routes.py`
só tem archive/restore e um DELETE que arquiva. `request_purge`/
`confirm_purge` só existem hoje para `employees`/`epis`. D18-D22 pedem
governança de exclusão definitiva para "colaborador/empresa" — mas para
empresa terceirizada isso simplesmente não existe ainda para ajustar. PR E
passa a incluir construir as rotas de exclusão definitiva de
`outsourced_companies` (`request`/`cancel`/`confirm`/resumo de histórico),
não só a precondição compartilhada em `ensure_purge_allowed` — mesmo padrão
já usado em `modules/employees/routes.py`.

**Mesmo bug do §13.19 (unit_id), agora em `outsourced_company_id` (P1).**
`update_employee_outsourced_simplified` valida e grava
`outsourced_company_id` do payload incondicionalmente, validado só contra
o vínculo da Unidade **do ator**. Depois que o PR D amplia o gate
administrativo por OR, a Unidade B (vinculada) poderia editar o
colaborador e trocar o fornecedor de X para Y — validado só para B — e essa
troca é **global**: a Unidade A perde a pessoa se Y não estiver vinculada
lá, e o empregador do colaborador muda para todo mundo a partir de uma
edição feita por uma Unidade que não é nem a de origem. Mesma correção do
achado P1 do §13.19: `update_employee_outsourced_simplified` preserva
`current['outsourced_company_id']` nesta edição — trocar de empresa
terceirizada exige um fluxo administrativo dedicado e auditado, não a
edição comum de um vínculo local.

**Achados de robustez de migração/concorrência, aceitos com ajuste:**

- **Backfill não deveria ativar vínculo para colaborador já arquivado
  globalmente.** Semear `employee_unit_links` ativo para toda `employees`
  com `outsourced_company_id`, sem olhar `status`, dá vínculo ativo a quem
  já estava arquivado/pendente de exclusão antes desta extensão sequer
  existir — e a nova precondição do PR E (nenhum vínculo ativo) passaria a
  bloquear a exclusão de gente que já estava no caminho certo. Ajuste:
  backfill filtra por status operacional (mesmo `NON_OPERATIONAL_STATUSES`
  já usado em `fetch_employees`) ou semeia `local_status = 'inactive'` para
  quem já não é operacional.
- **Checagem de vínculo ativo no purge não é atômica dentro de
  `confirm_purge`.** Rodar a checagem nas duas etapas (§13.19) fecha a
  janela ENTRE as etapas, não a janela DENTRO da confirmação — em
  PostgreSQL, uma Unidade pode ativar/criar vínculo entre o `SELECT` que
  confirma "nenhum ativo" e o `UPDATE` que marca a exclusão. Aceito como
  risco real, mesmo tratamento da corrida de CPF (§13.19): resolver de
  verdade exige lock explícito (`SELECT ... FOR UPDATE`) ou constraint a
  nível de banco no momento do `confirm_purge` — direção registrada, não
  implementada nesta ADR; decisão de design a confirmar no PR E.

**Pergunta nova em aberto — não decidida aqui, ao contrário do gate de
entrega em si (§13.9), que já foi fechado.** Arquivamento local
(`employee_unit_links.local_status = 'inactive'`) não bloqueia entrega
mesmo quando a Unidade arquivada **é** a Unidade atual de movimentação do
colaborador — `modules/deliveries/service.py` não consulta
`employee_unit_links` em nenhuma direção. Isto é diferente da pergunta já
fechada sobre ampliar o gate por OR (autorizar MAIS): aqui a pergunta é se
o gate precisa de uma restrição a MAIS (uma precondição negativa: bloquear
quando a Unidade atual está localmente arquivada), o que tecnicamente
ainda respeita "não ampliar por OR" mas contraria "`modules/deliveries/`
não é tocado por nenhum PR desta extensão" (§13.9/§13.16). Não decido isto
unilateralmente, dado que o usuário já foi explícito sobre não tocar
entrega — registrado para confirmação:

> **Pergunta**: arquivar localmente um colaborador na Unidade onde ele está
> atualmente alocado deve bloquear novas entregas ali (exige tocar
> `modules/deliveries/service.py` com uma checagem adicional, só
> restritiva, nunca uma nova autorização), ou o arquivamento local continua
> sendo só administrativo/de seleção nesta rodada — coerente com D13-D17
> mas sem dentes na entrega — e o bloqueio real de entrega para gente
> arquivada localmente fica para um PR futuro dedicado a
> `modules/deliveries/`?

### 13.21 Revisão automatizada (Codex) — rodada 3

Terceira rodada, disparada pelo push do §13.20. Dois achados apontavam para
o **PR A já implementado e aberto** (não só desenho futuro) — verificados
diretamente no código e **corrigidos de fato**, não só documentados aqui.

**Achado que expunha o PR A incompleto (P1) — corrigido.**
`create_employee`/`update_employee` (endpoint **geral** de colaborador,
`/api/employees`, não o Cadastro Simplificado) sempre aceitaram
`tipo_vinculo != 'CLT'` com `outsourced_company_id` preenchido — nada
nessas duas funções rejeitava a combinação — e ambas chamavam
`resolve_employee_legal_entity_id` **incondicionalmente**, exatamente como
`create_employee_outsourced_simplified` chamava antes do §13.7. Ou seja: o
mesmo alerta de produção podia ser reproduzido por um caminho diferente que
o PR A original nunca tocou. Pior: `update_employee` fazia
`current.get('legal_entity_id') or resolve_employee_legal_entity_id(...)`
— uma linha terceirizada já limpa pela migração (`legal_entity_id = NULL`)
tinha esse valor **repopulado** só por sofrer uma edição comum via este
endpoint. Corrigido: as duas funções só resolvem/gravam `legal_entity_id`
quando `tipo_vinculo == 'CLT'` — mesmo discriminador que `empresa_origem`
já usa nessas mesmas funções, nenhum conceito novo. Testado (4 testes
novos, incluindo não regressão para CLT com múltiplos CNPJs ativos) e já
enviado como novo commit no PR A.

**Achado sobre a migração de limpeza (P2) — corrigido.**
`outsourced_company_id IS NOT NULL` sozinho não é um discriminador seguro
para a migração: como o achado acima confirma, `create_employee` sempre
aceitou gravar `outsourced_company_id` **independente** de `tipo_vinculo`
— uma linha genuinamente CLT pode ter `outsourced_company_id` preenchido
(motivo legítimo ou não, não é desta ADR decidir) e continuar precisando do
seu `legal_entity_id`. Corrigido: a migração passa a exigir também
`tipo_vinculo <> 'CLT'` — só a combinação real do bug (terceirizado com
CNPJ do tenant indevidamente gravado) é limpa; qualquer linha CLT mantém
seu vínculo jurídico intacto, testado explicitamente.

**Achado de documentação (P2) — corrigido.** A seção original do PR A
descrevia o rollback como "reverter o commit, sem migração de dado
envolvida" — impreciso: a migração de limpeza (`UPDATE ... SET
legal_entity_id = NULL`) **não é reversível por rollback de código** — os
valores originais são perdidos, não há backup automático. Corrigido: PR A
documenta a limpeza como irreversível sem backup prévio; reverter o código
impede *novas* gravações indevidas mas não recupera o que já foi limpo.

**Achados de desenho (PR B/D, ainda não implementados) — incorporados:**

- **Transferência definitiva quebra disponibilidade depois do rollout do
  PR D.** Quando um colaborador vinculado só à Unidade A é definitivamente
  transferido para B (fluxo de movimentação existente, intocado por
  desenho), `employee_unit_links` continua apontando só para A —
  exatamente como projetado (§13.11: vínculo local não sincroniza com
  transferência). Mas depois que o PR D fizer os seletores dependerem de
  vínculo ativo, isso vira uma regressão real: a transferência "sucede" do
  ponto de vista do movimento, só que B não consegue selecionar o
  colaborador e A pode continuar listando-o — diferente do comportamento
  atual, guiado por `current_unit_id`. Ajuste: PR D precisa exigir/criar um
  vínculo ativo para a Unidade de destino como parte do fluxo de
  transferência definitiva (não como sincronização automática contínua,
  só neste ponto específico — na conclusão da transferência), ou definir
  explicitamente esse comportamento como aceito, não como "não regressão".
- **Backfill do PR B pode orfanar colaborador já transferido antes do
  rollout.** Combinado com a exigência do §13.20 (vínculo do colaborador
  requer vínculo ativo da empresa empregadora na mesma Unidade): se o
  colaborador foi transferido de A para B **antes** do PR B rodar, mas o
  vínculo da empresa terceirizada (§12.8) só existe para A, o backfill cria
  o vínculo do colaborador em B e ele é imediatamente rejeitado por falta
  de vínculo de empresa ativo ali. Ajuste: o backfill do PR B precisa
  também backfillar o vínculo de empresa correspondente para cada Unidade
  onde um colaborador seedado aterrissa, não só replicar o que o §12.8 já
  fez.
- **Ampliação do gate por OR vazaria para as rotas de ciclo de vida
  globais.** `_load_employee_for_lifecycle` (usada por
  `handle_post_employee_archive`/`restore`) chama
  `ensure_actor_employee_scope` — a mesma função que o PR D amplia por OR.
  Sem uma restrição adicional, um Administrador Local da Unidade B com
  vínculo ativo a um colaborador baseado em A ganharia acesso às rotas de
  arquivamento/restauração **globais** (`archive_record`/`restore_record`
  na linha inteira de `employees`), arquivando/restaurando o colaborador
  para **todas** as Unidades — contradizendo D13-D15 ("efeito só local").
  Ajuste: as rotas de ciclo de vida globais continuam exigindo a Unidade
  atual (sem a ampliação por OR); só as rotas novas de
  arquivar/desarquivar **local** (`employee_unit_links.local_status`) usam
  o gate ampliado. A ampliação por OR serve para visualizar/editar dados
  básicos e o vínculo local em si — nunca para acionar
  `core.archival`/`request_purge`/`confirm_purge` na linha compartilhada.

### 13.22 Revisão automatizada (Codex) — rodada 4

Quarta rodada, disparada pelo push do §13.21. Nenhum achado desta rodada
aponta para o PR A (já corrigido e estável nas duas rodadas anteriores) —
todos são sobre o desenho do PR B/C/D, ainda não implementado. Cinco
achados, todos aceitos:

- **A correção de disponibilidade por Unidade (§13.21) cobriu só
  transferência definitiva — temporária tem a mesma regressão.** Quando a
  janela de uma movimentação `temporary` começa, `get_employee_current_unit`
  passa a devolver a Unidade de destino — se ela não tiver vínculo ativo, o
  colaborador some do seletor lá mesmo estando operacionalmente presente,
  e a Unidade de origem pode recusar a entrega por já não ser mais a
  Unidade atual. Ajuste: a mesma exigência de vínculo ativo (colaborador +
  empresa empregadora) na Unidade de destino se aplica a transferência
  temporária, não só definitiva.
- **Achado crítico: o helper de disponibilidade, aplicado sem condição a
  `fetch_employees`, apagaria todo o quadro CLT dos seletores.** Todo
  colaborador CLT tem `unit_id` preenchido (nunca é "sem Unidade de
  origem") e, por D7/§13.11, nunca recebe `employee_unit_links` — as duas
  coisas juntas significam que um predicado "disponível só com vínculo
  ativo", aplicado genericamente, rejeitaria **100% do quadro próprio**,
  não só quem deveria. Isto já estava implícito no §13.4 ("não se aplica a
  pessoa, já que toda `employees` tem `unit_id`") mas a consequência nunca
  foi declarada explicitamente. Ajuste, agora explícito: o predicado de
  disponibilidade só se aplica a linhas com `outsourced_company_id`
  preenchido — colaborador CLT continua exatamente na lógica atual de
  Unidade atual computada, sem depender de `employee_unit_links` em nenhum
  momento. PR D precisa condicionar a chamada do helper a
  `outsourced_company_id IS NOT NULL`, não aplicá-lo à lista inteira.
- **Mesma classe de vazamento do gate por OR (terceira e quarta
  ocorrência) — rotas de portal do colaborador.** `modules/portal/routes.py:297-395`
  (gerar/contatar/revogar vínculo de portal) também chama
  `ensure_actor_employee_scope` e opera sobre um token único por
  colaborador (não por Unidade). Sem a mesma restrição já aplicada a
  arquivamento/restauração (§13.21), a Unidade B (só vinculada) poderia
  revogar/regenerar o token que a Unidade A está usando. Ajuste: mesma
  regra geral, agora reafirmada como princípio — **a ampliação por OR de
  `ensure_actor_employee_scope` vale só para leitura/edição de dados
  básicos e o vínculo local em si; qualquer rota que mute um recurso único
  e compartilhado por colaborador (ciclo de vida global, token de portal, e
  qualquer outra que a auditoria do PR D encontrar) mantém a exigência da
  Unidade atual, sem a ampliação.**
- **Dados de contrato na desambiguação (D4/D5) podem vazar entre
  Unidades.** Mostrar `contract_ref`/`service_order_ref` na lista de
  empresas "disponíveis" (ainda não vinculadas) exporia dado operacional de
  contrato de uma Unidade para outra — o oposto do que
  `annotate_outsourced_company_visibility` já mascara deliberadamente para
  empresa não vinculada (§12.3). Ajuste: PR C só mostra contrato quando já
  existe vínculo local ativo do ator com a empresa candidata; caso
  contrário omite esse campo específico na desambiguação (Razão Social/
  Nome Fantasia/CNPJ/tipo continuam aparecendo normalmente).
- **PR C depende do PR B, não é independente como a ordem sugeria.** O
  fluxo "CPF já cadastrado → vincular" (§13.4/§13.19) precisa gravar a
  ativação em `employee_unit_links` — schema e rota que só existem depois
  do PR B. Ajuste: ordem revisada para **A → B → (C depende de B; D
  depende de B) → E** — C e D deixam de ser posicionados como paralelos
  livres a B; ambos dependem dele, podem ser paralelos *entre si*.

**Nota de escopo:** as quatro rodadas de revisão até aqui já cobriram o
desenho do PR B-E com bastante profundidade — os achados desta rodada são
refinamentos incrementais de princípios já estabelecidos (disponibilidade
por Unidade, contenção do OR a rotas seguras), não descobertas de uma
classe nova de problema. Novas rodadas continuarão sendo endereçadas
achado a achado se chegarem, mas a partir daqui a implementação real do PR
B com sua própria suíte de testes é o próximo passo mais produtivo para
achar o que resta — não mais uma revisão adicional de um documento sem
código.

### 13.23 Revisão automatizada (Codex) — rodada 5

Quinta rodada, dois achados, ambos extensões estreitas de princípios já
estabelecidos — sem classe nova de problema:

- **Backfill de movimentação temporária futura.** O ajuste do §13.22
  (backfill cobre transferência temporária, não só definitiva) ainda
  assume "a movimentação ativa hoje" — uma movimentação `temporary` já
  **agendada** para o futuro (`start_date` posterior à data do backfill,
  já permitido pela rota de movimentação existente) fica de fora, porque
  `get_employee_current_unit` só considera janelas ativas na data da
  consulta. Quando essa janela futura começar, o destino ainda não terá
  vínculo. Ajuste: o backfill do PR B semeia vínculo (colaborador + empresa
  empregadora) para **toda** movimentação temporária não expirada — a
  ativa hoje e qualquer agendada para começar depois —, não só a atual.
- **Purge de empresa terceirizada não olha vínculo de colaborador.**
  A precondição de exclusão definitiva de `outsourced_companies` (§13.20,
  "nenhum vínculo ativo em nenhuma Unidade") checa
  `outsourced_company_unit_links`, mas desativar todos os vínculos da
  *empresa* não desativa os vínculos dos *colaboradores* dela —
  `employee_unit_links` é independente. Excluir a empresa nessas
  condições deixaria colaboradores com vínculo local ativo apontando para
  um fornecedor que não existe mais. Ajuste: o purge de
  `outsourced_companies` (PR E) também rejeita quando existe
  `employee_unit_links` ativo de qualquer colaborador cujo
  `outsourced_company_id` seja o da empresa sendo excluída, não só os
  vínculos diretos da empresa.
