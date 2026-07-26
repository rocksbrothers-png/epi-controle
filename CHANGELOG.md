# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento adota [SemVer](https://semver.org/lang/pt-BR/).
Os commits seguem [Conventional Commits](https://www.conventionalcommits.org/pt-br/):
`feat` (minor), `fix` (patch), `BREAKING CHANGE` (major), além de
`chore`/`docs`/`refactor`/`test`/`ci`.

## [Unreleased]

### Added
- Multi-CNPJ Fase 4 — conformidade: escopo de visibilidade por CNPJ
  (`user_legal_entities`, migration 017) — Administrador Local restrito aos
  CNPJs autorizados e Usuário restrito ao CNPJ do próprio colaborador, com
  lista vazia = sem restrição para não travar usuários existentes; CNPJ passa a
  ser obrigatório no colaborador quando a empresa tem mais de um CNPJ ativo
  (empresa de CNPJ único mantém o fallback); `company_audit_logs.legal_entity_id`
  registra o CNPJ afetado; exportação da ficha (LGPD) informa Empresa/CNPJ/
  Unidade com o CNPJ jurídico do colaborador; nova rota
  `DELETE /api/legal-entities/{id}` como inativação auditada (bloqueia o último
  CNPJ ativo e CNPJ com colaboradores vinculados) e
  `GET|PUT /api/users/{id}/legal-entities` para gerir a autorização.
- Multi-CNPJ Fase 3 — estoque, requisições e compras por CNPJ: nova configuração
  `stock_control_scope` (Empresa / CNPJ / Unidade) e `org_structure_type` em
  *Minha Empresa*; pool de estoque derivado de `units.legal_entity_id`
  (`resolve_stock_pool_unit_ids`) e saldo agregado por escopo
  (`fetch_scoped_stock_balance`) — o saldo físico segue por unidade, sem
  re-chavear a tabela nem migrar dados; requisições expõem o CNPJ derivado do
  solicitante; pedidos de compra ganham `legal_entity_id` (migration 016) por
  ser escolha de emissão, com NULL = pedido da empresa. A baixa de estoque na
  entrega permanece inalterada (ver ADR-0001 seção 9).
- Multi-CNPJ Fase 2 — rastreabilidade operacional por CNPJ: entregas expõem o
  CNPJ derivado do colaborador, completando a cadeia QR → Entrega → Colaborador
  → CNPJ → Empresa; unidades aceitam `legal_entity_id` (validado por empresa);
  portal do colaborador mostra Empresa/CNPJ/Unidade e registra
  `legal_entity_id`/`company_tax_id`/`unit_id` na auditoria; relatórios ganham
  filtro `legal_entity_id`; criação/alteração de CNPJ passa a ser auditada em
  `company_audit_logs`. O CNPJ é sempre derivado do vínculo do colaborador
  (fonte única, sem duplicação), via helper compartilhado
  `employee_legal_entity_sql`.
- Arquitetura Multi-CNPJ / Joint Venture (Fase 1 — fundação de backend): nova
  entidade `LegalEntity` (tabela `legal_entities`), permitindo que uma empresa
  possua um ou vários CNPJs (matriz, filiais, subsidiárias, SPEs, sócias de JV).
  Inclui migração idempotente com backfill automático da matriz padrão por
  empresa (nenhum dado perdido), API de CNPJ (`/api/legal-entities`, cadastro em
  lote), vínculo `employees.legal_entity_id` (opcional → retrocompatível),
  `units.legal_entity_id`, `companies.org_structure_type` e
  `companies.stock_control_scope`. RBAC:
  `legal_entities:{view,create,update,delete}`. Faturamento segue sendo do
  Tenant — CNPJs não alteram a assinatura SaaS. Ver
  `docs/adr/ADR-0001-arquitetura-multi-cnpj-legal-entity.md`.
- Infraestrutura de CI/CD fundacional: Dependabot, CodeQL (Python + JavaScript),
  workflow de Segurança (Dependency Review, Secret Scan via gitleaks, pip-audit).
- `backend-ci.yml`: pytest com cobertura, lint com ruff e validação PostgreSQL 16
  + invariantes Multi-Tenant (RLS / tenant_id) — substitui o antigo Python CI.
- `contract-tests.yml`: testes de contrato de API (envelope, enums, escopo).
- Governança: `CODEOWNERS`, template de Pull Request, templates de Issue
  (bug/feature), agrupamento automático de Release Notes.
- Documentação da infra de CI/CD em `docs/ci-cd/README.md`.

### Changed
- Removido `node.js.yml` (Python CI) em favor de `backend-ci.yml`.
