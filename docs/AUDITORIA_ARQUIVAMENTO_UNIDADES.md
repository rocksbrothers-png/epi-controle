# Auditoria e Política de Arquivamento (Soft Delete) de Unidades

Data: 2026-07-14 · Escopo: módulo de Unidades (API, banco, Web, Flutter)

## 1. Diagnóstico da implementação anterior

O fluxo `DELETE /api/units/{id}` executava **exclusão física em cascata**
(`delete_unit_dependencies` + `DELETE FROM units`), removendo permanentemente:

- Colaboradores da unidade, seus vínculos de usuário (`users.linked_employee_id`),
  links do portal e **logs de auditoria do portal**;
- EPIs escopados à unidade, itens de estoque/QR Codes, reimpressões de etiqueta,
  movimentações de estoque e saldos (`unit_epi_stock`);
- Entregas, requisições de EPI + histórico, avaliações/feedbacks + histórico;
- Itens e períodos de Ficha de EPI;
- Movimentações de colaboradores entre unidades.

A UI Web e o app Flutter confirmavam a operação com a mensagem
"apagará permanentemente a unidade e todos os registros vinculados".

### Falhas encontradas

1. **Perda irreversível de histórico** exigido por auditoria, compliance,
   investigações de acidente e NR-6 (ficha de EPI): tudo era apagado no ato.
2. **Logs de auditoria apagados junto** (`employee_portal_audit_logs`),
   violando o princípio de trilha imutável.
3. **Bug latente:** o código deletava da tabela inexistente
   `employee_portal_audit` (nome correto: `employee_portal_audit_logs`) —
   em PostgreSQL, o DELETE de unidade com colaboradores retornava **500**.
4. **FKs RESTRICT quebravam o fluxo:** `purchase_requests`, `purchase_orders`,
   `ficha_epi_snapshots`, `epi_devolutions` e `unit_joint_venture_periods`
   referenciam `units(id)` e não eram tratados — o DELETE falhava (Postgres)
   ou deixava registros órfãos (SQLite sem FK enforcement).
5. **Sem ciclo de vida:** não existia `status`, retenção, bloqueio jurídico
   nem mecanismo algum de soft delete no projeto.
6. **Sem auditoria da exclusão:** nenhum registro de quem, quando, por quê.

## 2. Política implementada

### Ciclo de vida da Unidade (`units.status`)

| Status | Significado |
| --- | --- |
| `active` | Ativa — operação normal |
| `inactive` | Inativa — marcação operacional (POST `/api/units/{id}/status`) |
| `archived` | Arquivada — soft delete; histórico 100% preservado |
| `pending_deletion` | Em processo de exclusão (etapa 1/2 confirmada) |
| `deleted` | Excluída definitivamente — permanece como *tombstone* |

### Regras

- **`DELETE /api/units/{id}` não remove mais nada**: arquiva a unidade
  (compatibilidade retroativa para clientes antigos).
- Arquivamento grava `archived_at`, `archived_by`, `archive_reason` e
  `retention_until` (= data do arquivamento + retenção do tenant).
- **Retenção configurável por tenant** em `companies.unit_retention_years`
  (GET/PUT `/api/units/retention-policy`), com **piso obrigatório de 5 anos**.
- Unidade arquivada **bloqueia**: novos colaboradores, transferências para ela,
  novos EPIs, entregas, movimentações/recebimento de estoque, requisições de
  EPI e requisições/pedidos de compra (guard `ensure_unit_operational` em
  todos os pontos de escrita). **Permite**: consultas, relatórios, auditorias
  e impressão — nenhuma consulta histórica filtra por status.
- **Bloqueio jurídico** (`legal_hold` + motivo) impede a exclusão definitiva
  enquanto ativo (POST `/api/units/{id}/legal-hold`, Admin Geral/Master).
- **Exclusão definitiva em duas etapas**, apenas Admin Geral ou Master, apenas
  após a retenção expirar e sem legal hold:
  1. `POST /api/units/{id}/purge-request` → valida elegibilidade, retorna o
     **resumo completo dos registros** que serão removidos e marca
     `pending_deletion` (cancelável via `purge-cancel`);
  2. `POST /api/units/{id}/purge-confirm` → exige **justificativa (≥ 10
     caracteres)** e a **digitação do nome exato da unidade**; expurga os dados
     operacionais e converte a unidade em *tombstone* (`status='deleted'`,
     `deleted_at`, `deleted_by`, `delete_reason`) — o `unit_id` e o
     `company_id` **nunca saem do banco**, preservando FKs e rastreabilidade.
- **Auditoria permanente** em `company_audit_logs` (reuso da trilha existente)
  para arquivar/restaurar/status/legal hold/purge, com usuário, data/hora, IP,
  motivo, retenção aplicada e resumo dos registros — esta trilha **não** é
  expurgada.
- **Multi-tenant**: todas as operações validam `company_id` via
  `ensure_resource_company`; a listagem de arquivadas é filtrada por tenant e
  a retenção é independente por empresa.

## 3. Alterações por camada

### Banco de dados

- `core/schema.py`: colunas novas em `units` (status, archived_*, retention_until,
  legal_hold*, deleted_*), `companies.unit_retention_years`, índice
  `idx_units_status`, migração idempotente `ensure_unit_lifecycle_columns`.
- `supabase/migrations/20260714000000_unit_archival_soft_delete.sql`: mesmas
  colunas + CHECK constraint do ciclo de vida (Postgres/Supabase).
- Nenhuma FK alterada; nenhum `unit_id` é removido de registros históricos.

### API (`modules/units`)

- `DELETE /api/units/{id}` → arquiva (era hard delete).
- Novos endpoints: `GET /api/units/archived`, `POST /{id}/archive`,
  `/{id}/restore`, `/{id}/status`, `/{id}/legal-hold`,
  `GET /{id}/deletion-summary`, `POST /{id}/purge-request|purge-cancel|purge-confirm`,
  `GET|PUT /api/units/retention-policy`.
- `GET /api/units` e o bootstrap passam a listar apenas unidades operacionais
  (arquivadas saem de dropdowns e telas operacionais).
- Guards em `employees`, `deliveries`, `stock`, `purchases`, `portal` e `epis`.

### Frontend Web

- Botão "Remover" → **"Arquivar"** com a mensagem de retenção exigida.
- Nova área **"Unidades Arquivadas"** na tela de Unidades com filtros por
  Empresa, Data de arquivamento, Motivo e Responsável + coluna de retenção
  restante, ações Restaurar e Excluir definitivamente (fluxo em 2 etapas).
- i18n atualizado (pt-BR completo; demais locales com fallback em inglês).

### Flutter

- `UnitsApi`: `archiveUnit`, `restoreUnit`, `getArchivedUnits` (o `deleteUnit`
  legado permanece e hoje arquiva no backend).
- `UnitsCubit.deleteUnit` → `archiveUnit(reason)`.
- Tela de Unidades: menu "Excluir" → "Arquivar" com diálogo informando a
  retenção mínima de 5 anos e campo de motivo para auditoria.

## 4. Plano de testes (implementado em `tests/test_unit_archive.py`)

- Arquivar preserva 100% dos registros vinculados e grava auditoria com IP/motivo.
- Retenção mínima de 5 anos aplicada; configurável por tenant; rejeita < 5.
- Arquivada sai da listagem principal e aparece na listagem de arquivadas.
- Isolamento multi-tenant da listagem de arquivadas.
- Bloqueio de novas operações em unidade arquivada; unidade ativa segue livre.
- Restauração reativa a unidade e limpa metadados de arquivo.
- Purge bloqueado: durante retenção, sem arquivamento prévio, por perfil sem
  permissão e por bloqueio jurídico.
- Fluxo completo de purge em 2 etapas: resumo, justificativa obrigatória,
  confirmação por nome, tombstone, expurgo e trilha de auditoria em 3 eventos.
- Compatibilidade com schemas legados sem as colunas novas (testes antigos).

## 5. Garantia de preservação

Enquanto `status='archived'`: nenhuma linha vinculada é alterada ou removida;
relatórios, fichas, dashboards e consultas históricas continuam funcionando
porque nenhuma query de leitura filtra por status. A exclusão física só é
possível após `retention_until` (≥ 5 anos), sem bloqueio jurídico, com dupla
confirmação de Admin Geral/Master — e mesmo então o registro da unidade e a
trilha de auditoria permanecem para sempre.

---

## 6. Extensão da política: Colaboradores e EPIs (2026-07-18)

A mesma política de arquivamento das Unidades foi estendida a **Colaboradores**
e **EPIs**, com núcleo genérico em `core/archival.py`:

- **Arquivar** (`DELETE /api/{employees|epis}/{id}` ou `POST /{id}/archive`):
  registro desativado para novas operações — colaborador arquivado não recebe
  entregas, requisições nem movimentações; EPI arquivado não entra em entregas,
  estoque, requisições nem compras. Histórico 100% preservado; listagens
  principais e bootstrap passam a exibir apenas registros operacionais.
- **Desarquivar** (`POST /{id}/restore`): volta ao status ativo.
- **Exclusão definitiva** habilitada **somente após a retenção** do tenant
  (mínimo 5 anos — mesmo parâmetro `companies.unit_retention_years`); até lá o
  registro permanece arquivado. Duas etapas (`purge-request` com resumo →
  `purge-confirm` com justificativa ≥ 10 caracteres + nome exato), apenas
  Admin Geral/Master, sem bloqueio jurídico; o registro vira tombstone
  (`status='deleted'`) e a trilha em `company_audit_logs`
  (`employee_*`/`epi_*`) é permanente, com usuário, data/hora, IP, motivo e
  resumo dos dados removidos.
- **Banco**: colunas de ciclo de vida em `employees` e `epis`
  (`ensure_archival_lifecycle_columns` + migração Supabase
  `20260716000000_employee_epi_archival_soft_delete.sql`), índices
  `(company_id, status)` e CHECK do ciclo de vida.
- **Web**: abas "Arquivados" em Colaboradores e EPIs com filtros (empresa,
  data, motivo, responsável), retenção restante, Desarquivar e Excluir
  definitivamente (2 etapas, pós-retenção).
- **Flutter (Android/iOS)**: ação Arquivar com motivo nas telas de
  Colaboradores e EPIs + alternância Ativos ⇄ Arquivados com Desarquivar.
- **Fix adicional**: o DELETE legado de colaborador fazia `DELETE FROM
  employees` sem tratar dependências (falha de FK/órfãos); o fluxo agora é
  soft delete e o expurgo pós-retenção trata todas as tabelas dependentes.
- **Testes**: `tests/test_entity_archive.py` (9 casos) cobrindo preservação,
  bloqueio, desarquivamento, purga pós-retenção, papel exigido, justificativa,
  nome exato e compatibilidade com schema legado.
