# ADR-0002 — Cadastro Simplificado de Terceirizados e Prestadores

- **Status:** Aceito — PR 1 (fundação de backend) implementado
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
(`cnpj_normalized`, só dígitos) com `UNIQUE(company_id, cnpj_normalized)`:
a mesma terceirizada nunca duplica dentro do mesmo tenant, mas o mesmo CNPJ
pode aparecer em tenants diferentes sem colisão (unicidade composta, não
global).

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
    UNIQUE(company_id, cnpj_normalized),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

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
   (já implementado neste PR 1 como fundação; PR 2 cobre telas e regras de
   apresentação Simplificado/Padrão).
3. **PR 3 — Cadastro dos colaboradores + migração + validações.**
4. **PR 4 — Integração com o fluxo existente de entrega** (leitura +
   snapshot histórico), sem alterar o fluxo em si.
5. **PR 5 — Auditoria, histórico e registro de responsabilidades.**
6. **PR 6 — Relatórios, custos, ressarcimento, dashboards, alertas
   inteligentes.**
7. **PR 7 — Flutter (Web, Android, iOS).**
8. **PR 8 — Web Legado.**
9. **PR 9 — Testes completos, regressão e documentação final.**

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
