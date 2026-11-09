# Compras CO-1 — Governança e alçadas de aprovação

Fatia **CO-1** do domínio Compras/Orçamento. Não confundir com as fatias UBX Comercial C1–C4, já concluídas.
Decisões aplicadas: **D-1** (só o Administrador Geral configura a alçada), **D-2** (limite por empresa, sem valor
padrão) e **D-17** (proibição de autoaprovação). Sem orçamento, centro de custo, compromisso ou cancelamento de PO.

## 1. Limite de alçada (D-1, D-2)

| Item | Regra |
|---|---|
| Fonte de verdade | A chave **existente** `po_approval_threshold` em `app_meta['purchase_config_{empresa}']`, lida pela aprovação de PO. Nenhuma tabela nova, nenhuma segunda fonte |
| Quem configura | Permissão nova `purchase_limits:manage`, concedida **somente** a `general_admin`. A empresa vem do ator, nunca do payload |
| Quem consulta | `purchase_limits:manage` ou `finance:view` (consulta). `finance:view` não concede edição |
| Ausência de limite | Sem valor padrão. Ausência = sem limite = **um nível** (comportamento anterior). Nunca lida como zero |
| Zero | **Recusado** (o valor precisa ser > 0). Para voltar a um nível, **remove-se** o limite (`value: null`), e a remoção é auditada |
| Representação | `Decimal` com 2 casas, em BRL (Compras não tem outra moeda). Armazenado como texto (`"15000.00"`). Mais de 2 casas, float, notação científica, sinal e separador de milhar são recusados, nunca arredondados |
| Comparação | `required_approval_levels` compara `total_value` e limite em `Decimal` (2 casas): `total ≥ limite` → 2 níveis. O formato legado numérico (`20000.0`) continua lido pela representação textual |
| Concorrência | Leitura-modificação-escrita sob trava da linha de configuração (`BEGIN IMMEDIATE` / `INSERT … ON CONFLICT DO NOTHING` + `SELECT … FOR UPDATE`) e versão otimista (`expected_version`, `409 PURCHASE_LIMIT_VERSION_CONFLICT`). A gravação de `require_admin_review` usa a mesma trava, para uma não apagar a outra |
| Auditoria | `purchase_events` (entidade `company`): `purchase_limit_created` / `_changed` / `_removed`, com valor anterior (`status_from`) e posterior (`status_to`), ator, papel e IP; `purchase_limit_conflict` para versão obsoleta |

### API

| Método | Rota | Permissão | Corpo / resposta |
|---|---|---|---|
| GET | `/api/purchase-limits` | `purchase_limits:manage` ou `finance:view` | `{ok, data: {po_approval_threshold: "15000.00" \| null, currency, configured, version, updated_at, updated_by_name, company_id, can_manage}}`. `master_admin` precisa informar `company_id` (consulta de suporte, sem edição) |
| POST | `/api/purchase-limits` | `purchase_limits:manage` | `{actor_user_id, value: "15000.00" \| null, expected_version, currency?: "BRL"}` → `200 {ok, data}` · `400` valor inválido · `403` sem permissão · `409 PURCHASE_LIMIT_VERSION_CONFLICT` |

Interface web: cartão em **Configuração** (`static/views/configuracao.html`), módulos
`static/js/modules/purchases/{business/purchase-limits-rules.js, integrations/purchase-limits-api.js, ui/purchase-limits-view.js}`.
Visível só com `purchase_limits:manage`. Nenhuma linha no `static/app.js`.

## 2. Segregação de funções (D-17)

| Operação | Regra no backend |
|---|---|
| Aprovar itens de requisição (`POST /api/purchase-requests/{id}/workflow`, ação `approve`) | Recusada se o aprovador for o criador da requisição (`PURCHASE_SELF_APPROVAL_FORBIDDEN`, 403). Reprovar continua permitido |
| Aprovar PO (`POST /api/purchase-orders/{id}/approve`, decisões `approved`/`partially_approved`) | Recusada se o aprovador for o criador do PO **ou** de qualquer requisição de origem (a do cabeçalho e as dos itens) |
| 2º nível do PO | Continua exigindo `finance:view` e aprovador diferente do 1º, agora **por pessoa** (`PURCHASE_SECOND_LEVEL_SAME_PERSON`) |
| Rota genérica `POST /api/purchase-requests/{id}/status` | Não aceita mais `approved`/`partially_approved` (`PURCHASE_APPROVAL_REQUIRES_WORKFLOW`). Nenhum cliente web ou Flutter usava essa rota para aprovar; ela era um atalho que contornava aprovador e segregação |

**Pessoa, não conta.** `users.linked_employee_id` não é único: a mesma pessoa pode ter várias contas (por exemplo,
Administrador Local e Aprovador). A identidade comparada é o conjunto de contas da empresa ligadas ao mesmo
colaborador. Trocar de conta não contorna a regra.

**Poucos usuários.** Não há exceção: sem outra pessoa autorizada, o registro fica pendente.

**Registros legados.** Criador ausente (`NULL`/0) não prova conflito: a aprovação segue e grava o evento
`segregation_unverifiable` junto da decisão. Nada libera quem **é** o criador comprovado. Os registros com esse
evento são a lista de regularização. Nenhum criador histórico é alterado.

**Auditoria da recusa.** Toda recusa de governança (403) ou conflito de estado (409) desfaz a transação da
tentativa e grava `approval_denied` / `approval_conflict` em transação própria, para o registro não sumir no rollback.

## 3. Concorrência na aprovação de PO

`approve_purchase_order` trava requisição → PO (mesma ordem do recebimento), **relê o PO sob a trava** e só então
valida estado, segregação e níveis. A alçada é lida na mesma transação (`FOR SHARE` no Postgres), então uma
alteração de limite em curso termina antes da decisão.

| Cenário | Resultado |
|---|---|
| Duas aprovações simultâneas | Uma 200; a outra `409 PURCHASE_ORDER_STATE_CHANGED` com o estado atual, sem gravar nada |
| Aprovação × rejeição simultâneas | Um único resultado persistido |
| Reenvio da mesma aprovação | 409, sem nova linha em `purchase_approvals` ou `purchase_events` |
| Mesmo aprovador (ou mesma pessoa) no 2º nível | 403, sem segunda linha |
| Falha no meio | Rollback integral (status, itens, aprovação, eventos) |

Provas: `tests/test_co1_purchase_approval_concurrency.py` (SQLite, conexões independentes) e
`tests_postgres/test_co1_purchase_approval_concurrency_postgres.py` (PostgreSQL, HTTP/JWT). Com a trava removida, os
testes reprovam (sabotagem verificada na entrega).

## 4. Fora do escopo e pendências

- **Flutter:** sem alteração de código. As regras valem para o app porque estão no backend; o app mostra a tela
  de erro genérica que já usava para qualquer recusa em ações de PO (inclusive a regra preexistente do 2º nível).
  Exibir as mensagens específicas por `code` é uma melhoria recomendada para fatia própria.
- **Migração:** nenhuma. A configuração continua em `app_meta`; as tabelas de auditoria existentes bastam.
- **Rollback:** reverter o commit. Limites gravados permanecem em `app_meta` e passam a ser lidos com a regra
  anterior (`float`, mesma semântica para valores válidos). Nenhum dado histórico é alterado.
