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
19. **D19.** Exclusão definitiva fica sob governança do Administrador Geral e da política de retenção já existente.
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
permanece `NULL` para toda linha com `outsourced_company_id` preenchido,
exatamente como já é `NULL` hoje para toda linha sem Multi-CNPJ provisionado
— nenhuma migração de dado necessária, é remoção de uma chamada, não
mudança de schema.

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

**D4/D5 têm duas leituras possíveis** e a diferença entre elas é grande o
bastante para precisar de confirmação explícita antes de qualquer PR:

- **Leitura mínima (recomendada):** `outsourced_companies` já permite hoje
  duas linhas com o mesmo `legal_name`/`trade_name` (CNPJs diferentes, ou
  ambas sem CNPJ — o índice único é por `cnpj_normalized`, não por nome).
  D4/D5 descreveriam então a busca/seleção de empresa no Cadastro de
  Colaborador: se a busca por nome encontra uma única `outsourced_companies`
  correspondente, associa automaticamente (D4, já é o comportamento atual);
  se encontra mais de uma (filiais/CNPJs distintos cadastrados como linhas
  separadas do mesmo prestador), a tela passa a exigir escolha explícita de
  qual `outsourced_company_id` em vez de pegar a primeira (D5) — reforço de
  UX/precisão sobre uma estrutura que já existe, sem tabela nova.
- **Leitura estrutural (mais pesada):** um Multi-CNPJ dedicado para empresa
  terceirizada, espelhando `legal_entities` mas para `outsourced_companies`
  (uma "prestadora" com N filiais/CNPJs formalmente agrupadas). Isso exigiria
  uma tabela nova (ex.: `outsourced_company_legal_entities`) e não tem
  menção explícita em nenhuma das 22 decisões — seria introduzir um conceito
  novo, o que vai contra a disciplina desta sessão ("não criar novos
  conceitos" já aplicado nas rodadas anteriores).

Recomendação: seguir a leitura mínima. Peço confirmação explícita antes de
incluir D4/D5 em qualquer PR (§13.15, PR C).

### 13.9 Impacto no fluxo existente de entrega de EPI

Entregas referenciam `employees.id` diretamente. Como D7 mantém uma única
linha `employees` por pessoa no tenant (nunca duplicada entre Unidades), o
histórico de entregas de um colaborador compartilhado passa a ser **um
único trilho**, de qualquer Unidade em que ele tenha atuado — o oposto do
risco atual, em que o beco sem saída do Problema B (§13.1) levaria, na
prática, a cadastros duplicados manuais e histórico de entrega fragmentado
em duas pessoas "diferentes" no sistema caso alguém contornasse o bloqueio
criando uma segunda pessoa com CPF ligeiramente diferente digitado.

O snapshot histórico da entrega (§3.5, já registra Unidade/empresa no
momento da entrega) não muda de comportamento — uma entrega feita enquanto
o colaborador estava vinculado à Unidade A continua mostrando a Unidade A
mesmo que esse vínculo seja arquivado depois (D22, preservar histórico).
O novo gate necessário é em tempo de **criação** de entrega: hoje
`ensure_record_operational`/checagens equivalentes bloqueiam operação
contra colaborador arquivado (globalmente); passam a também bloquear
quando o vínculo específico da Unidade que está lançando a entrega está
`inactive` em `employee_unit_links`, mesmo que o colaborador esteja ativo
em outra Unidade (D15/D16).

### 13.10 Impacto nos relatórios

`fetch_outsourced_employees_summary` (§11.5/§12.7) e qualquer relatório que
hoje filtra por `employees.unit_id` assumem implicitamente "1 linha = 1
Unidade". Com D7/D8, isso deixa de ser verdade: um relatório de headcount
por empresa/Unidade precisa decidir explicitamente se lê `employees.unit_id`
(Unidade de origem, histórica) ou faz `JOIN employee_unit_links WHERE
local_status = 'active'` (vínculo operacional atual) — a mesma distinção
que o §12.1 já introduziu para empresa, agora necessária para pessoa
também. Não é possível enumerar exaustivamente todos os relatórios afetados
nesta ADR; a implementação (§13.15, PR D) precisa de um passo de auditoria
dedicado nesses call sites antes de considerar o trabalho completo — risco
registrado em §13.13.

### 13.11 Migração necessária

- **Tabela nova `employee_unit_links`** (mesmo par dual-track já usado em
  todas as migrações desta sessão): SQLite via `core/schema.py`
  (`ensure_employee_unit_links`) + `core/bootstrap.py`; Postgres/Supabase
  via `epi_backend/migrations/0NN_employee_unit_links.py` +
  `supabase/migrations/*.sql` irmão, RLS habilitado desde a criação. Forma:
  `id, company_id, employee_id, unit_id, local_status ('active'|'inactive'),
  activated_at, activated_by_user_id, deactivated_at, deactivation_reason,
  deactivated_by_user_id, created_at, updated_at`, `UNIQUE(company_id,
  employee_id, unit_id)`.
- **Backfill**: toda `employees` com `unit_id` preenchido ganha uma linha
  `employee_unit_links` ativa para essa Unidade — idêntico em espírito ao
  backfill do §12.8, mesma exigência de idempotência.
- **`employees.unit_id` como metadado histórico imutável**: por analogia
  direta com o §12.1 (`outsourced_companies.unit_id`), a consequência
  natural de D7/D8 é que `employees.unit_id` também deveria congelar como
  "Unidade de origem" (gravado só na criação, nunca mais alterado), e o
  vínculo operacional passa a viver inteiramente em `employee_unit_links`.
  **Isto não está explicitamente nas 22 decisões** — é uma inferência por
  simetria com o que já foi decidido para empresa, não uma instrução
  verbatim. Peço confirmação explícita (§13.15 depende desta resposta para
  o desenho exato de PR B).
- **Correção de `create_employee_outsourced_simplified`/
  `update_employee_outsourced_simplified`** (§13.7) — mudança de código
  isolada, sem migração de schema associada.
- **UX de desambiguação D4/D5** (§13.8) — depende da leitura escolhida.

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
- **Ambiguidade D4/D5** (§13.8) — a leitura errada infla o escopo com uma
  tabela nova não pedida explicitamente.
- **Inclusão de `master_admin` na governança de exclusão definitiva** é
  comportamento **pré-existente** (`_require_deletion_admin` já permite
  `master_admin` e `general_admin`, não só o segundo) e está **fora do
  escopo desta extensão** — D19 pede "governança do Administrador Geral",
  o que não exclui Master explicitamente do jeito que o §12.5 excluiu Master
  da edição de dado corporativo por doutrina. Não estou alterando esse gate
  como parte deste ADR; registro aqui como pergunta em aberto, não como
  mudança proposta.
- **Corrida entre Unidades vinculando a mesma pessoa quase simultaneamente**
  — mesma proteção que `outsourced_company_unit_links` já usa
  (`UNIQUE(company_id, employee_id, unit_id)` + tratamento de conflito como
  "já vinculado", não erro).

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
  `general_admin` (e, até decisão em contrário, `master_admin` — risco
  registrado em §13.13) e ao fluxo de duas etapas já existente em
  `core/archival.py`; passa a também exigir ausência de vínculo ativo em
  qualquer Unidade (D18/D19/D21).
- Existe aviso antecipado quando um registro se aproxima da data de
  elegibilidade para exclusão definitiva (D20).
- Histórico de entregas, auditoria, contratos e demais registros
  obrigatórios permanecem intactos e consultáveis após qualquer
  arquivamento local (D22).
- Suíte de testes (backend + frontend, `pytest tests/ -q` e
  `node static/js/test/run-tests.js`) verde nos dois repositórios, incluindo
  testes novos para cada decisão D1-D22 tocada por código.

### 13.15 Divisão sugerida em PRs

- **PR A — correção isolada do alerta de CNPJ (§13.7).** Remove a chamada a
  `resolve_employee_legal_entity_id` do fluxo terceirizado simplificado.
  Menor PR possível, corrige o bug com reprodução real em produção, sem
  depender de nenhuma tabela nova. Candidato a seguir sozinho e primeiro.
- **PR B — `employee_unit_links`.** Schema + backfill (dual-track) +
  `is_employee_available_to_unit` + rotas de vincular/ativar/desativar
  vínculo local + testes, mesma forma do §12.2. Inclui a decisão sobre
  `employees.unit_id` virar metadado imutável (§13.11) — bloqueado até
  confirmação.
- **PR C — busca + vínculo no Cadastro de Colaborador.** CPF duplicado
  passa a oferecer "vincular" em vez de bloqueio surdo (mesma forma do
  §12.4); inclui a resolução de D4/D5 conforme a leitura confirmada
  (§13.8).
- **PR D — arquivar/desarquivar colaborador por Unidade.** Frontend +
  backend; seletores operacionais (Cadastro de Colaborador, entrega de EPI)
  passam a filtrar por `employee_unit_links.local_status`; inclui a
  auditoria de relatórios afetados (§13.10).
- **PR E — governança de exclusão definitiva.** Nova precondição em
  `ensure_purge_allowed` (nenhum vínculo ativo em nenhuma Unidade, D21) +
  aviso antecipado de elegibilidade (D20). Depende do PR B já estar
  mergeado.
- **PR F (condicional)** — só nasce se a leitura estrutural de D4/D5 for
  confirmada em vez da mínima: subsistema de Multi-CNPJ para
  `outsourced_companies`.

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
  `_require_deletion_admin` (§13.13) sem confirmação explícita — é
  comportamento pré-existente, fora do que as 22 decisões pediram
  literalmente.
