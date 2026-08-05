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
  PR 14 (Flutter) e PR 15 (Web Legado) — sequência completa, ver §10.6
- **Data:** 2026-07-29
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
