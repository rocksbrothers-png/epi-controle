# Auditoria Sistêmica de Lacunas Funcionais — EPI-CONTROLE

Data: 2026-07-18. Escopo do prompt: Web Legado, Flutter Web, Android, iOS e
Backend/API. Esta Fase 1 é fundamentada em **leitura do código** (o backend
centraliza as regras de negócio). Itens que dependem de reproduzir a UI ao vivo
estão marcados como tais — o ambiente de produção/staging (Render) não é
alcançável a partir do ambiente de auditoria (`curl` retorna `HTTP 000`).

## Método aplicado (por item)
1. Mapear o fluxo no código. 2. Localizar a falha. 3. Classificar
(Frontend/Backend/API/Banco/Permissão/Regra). 4. Verificar regressão recente.
5. Corrigir preservando compatibilidade. 6. Cobrir com teste.

## Achado sistêmico (causa comum de múltiplos 500 em produção)
Um único padrão explica a regressão do item 7, os três hotfixes recentes
(PRAGMA, `f.epi_name`, `GROUP BY` não-agregado) e provavelmente outros erros
"invisíveis": **código escrito e testado apenas em SQLite que quebra no
PostgreSQL de produção**. A suíte roda em SQLite in-memory e não pega:

| Sintoma em prod (Postgres) | Válido em SQLite? | Exemplo corrigido |
|---|---|---|
| `PRAGMA table_info(...)` → erro de sintaxe | sim | `epi_backend/ppe_test_schema.py` (#728/#49) |
| `GROUP BY x` com coluna nua no SELECT | sim | `compute_epi_evaluation_status`, `fetch_suggestion_ranking` (#729/#50) |
| coluna inexistente mascarada por outra falha | não* | `SELECT f.epi_name` (#729/#50) |
| texto de exceção divergente | — | guard de participante duplicado (#728/#49) |

**Recomendação de maior ROI:** adicionar ao CI um estágio que roda a suíte
contra PostgreSQL (serviço `postgres` no GitHub Actions + fixtures que usem o
wrapper `core.database`), OU no mínimo ampliar os guards estáticos de dialeto
(já existe `tests/test_no_sqlite_pragma_runtime.py`). Isso previne uma classe
inteira de quedas de produção sozinho.

## Itens do prompt

### Item 7 — "Computar Status do EPI" não funciona — ✅ CORRIGIDO
- **Classificação:** Backend/Banco. **Criticidade:** Alta.
- **Causa raiz:** `compute_epi_evaluation_status` fazia `GROUP BY f.epi_id`
  selecionando `e.name`, `e.company_id` (de `epis` juntada). PostgreSQL rejeita
  ("must appear in GROUP BY or aggregate") → 500 no clique do botão.
- **Correção:** `GROUP BY f.epi_id, e.name, e.company_id` (PRs #729/#50, merged).
  Requer redeploy do backend.
- **Teste:** `tests/test_feedback_ranking_dialect_compat.py`.

### Item 3/8 — Bloqueio de EPI não efetiva — ⚠️ precisa repro na UI
- **Classificação:** Backend/UX. **Criticidade:** Alta.
- **Mapa:** endpoint existe e está ligado — `POST /api/stock/items/status`
  → `handle_post_stock_item_status` → `set_stock_item_status`
  (`modules/stock/routes.py:135`, `modules/stock/service.py:443`). A lista usa
  `GET /api/stock/blocked-items` → `fetch_blocked_stock_items`.
- **Causa raiz provável:** o bloqueio opera sobre um **item individual
  com QR** (`epi_stock_items`), resolvido por `lookup_stock_item_by_qr`
  (qr_code OU stock_item_id). Se a tela envia o **código do produto/CA** (nível
  `epis`) em vez do QR do item, `lookup` não acha → "Item não encontrado", nada
  bloqueia. Também exige `unit_id` no payload e respeita unidade operacional.
- **Próximo passo:** print do console (payload enviado + resposta) para
  confirmar se é resolução de item (UX) ou erro de dialeto/permissão.

### Item 1 — EPI arquivado "some" (não vai para Estoque Bloqueado) — ⚠️ gap de design
- **Classificação:** Regra/UX. **Criticidade:** Alta.
- **Mapa:** arquivar o **EPI do catálogo** (`fetch_archived_epis`,
  `modules/epis/service.py:280`, tela "Arquivados") é distinto de **bloquear
  itens de estoque**. Estoque Bloqueado só lista `epi_stock_items` com status
  `blocked_*`. EPI arquivado não é item bloqueado → não aparece lá.
- **Decisão de produto pendente:** ao arquivar um EPI com estoque, o esperado é
  (a) mover os itens para bloqueado, (b) impedir arquivar com saldo, ou
  (c) refleti-lo numa aba própria? Precisa alinhamento antes de codar (evita
  regressão em entrega/FEFO).

### Item 6 — Aba Cotações não abre — ⚠️ provável frontend/permissão
- **Classificação:** Frontend/Permissão. **Criticidade:** Média.
- **Mapa:** módulo implementado — `modules/purchases/quotes_routes.py`
  registrado via `_register_quotes_routes` (`modules/purchases/routes.py:705`);
  aba e painel existem (`static/views/compras.html:13,408`).
- **Causa raiz provável:** erro de JS ao abrir o painel, ou permissão
  `quotes:view` ausente para o perfil. Precisa do console para confirmar.

### Item 9 — Comprador/Aprovador não aparecem — ℹ️ provável deploy antigo
- **Classificação:** Frontend/Deploy. **Criticidade:** Baixa.
- **Mapa:** `populateRoleOptions` (`static/app.js:3547`) já inclui `buyer` e
  `approver` para Admin Geral; filtro idem; backend aceita
  (`modules/users/service.py:44`). Código atual suporta. Verificar após redeploy.

### Item 2 — Dashboard "CA vencido" diverge da tela operacional — 🔎 a traçar
- **Classificação:** Backend/Regra. **Criticidade:** Média.
- **A investigar:** comparar a query do card do dashboard com a de "Validade e
  Bloqueios" — timezone, `ca_expiry` vs `epi_validity_date`, item disponível vs
  bloqueado. Alinhar fonte única e o clique abrindo exatamente os itens do card.

### Item 5 — Movimentações sem colunas de vencido/bloqueado — 🔎 frontend
- **Classificação:** Frontend. **Criticidade:** Baixa.
- Acrescentar colunas Status/CA/fabricação/validade/bloqueio + indicadores
  visuais (🟢🟡🔴⚫) e ordenação na tabela de movimentações.

### Item 4 — QR Code de entrega não identifica colaborador — 🔎 melhoria
- **Classificação:** Backend+Frontend. **Criticidade:** Média.
- Enriquecer o payload do QR (colaborador, matrícula, empresa, unidade, EPI,
  lote, tamanho, nº da entrega, data) e fechar o fluxo atualizando o Portal do
  Colaborador (Entregue/Data/Responsável/Assinatura) automaticamente.

## Priorização recomendada
1. **CI Postgres-parity** (previne a classe inteira; sem repro necessária).
2. **Item 1** (alinhar regra de arquivamento×estoque — decisão de produto).
3. **Item 3/8** e **Item 2** (precisam de console/log de produção).
4. **Itens 5 e 4** (frontend/enhancement).
5. **Item 9** (revalidar pós-redeploy).

## Rollback
Cada correção sai em PR isolado por item, com teste e revertível por
`git revert` do merge. Nenhuma migração destrutiva; tabelas/colunas novas são
aditivas e idempotentes.

## Pendências para fechar a auditoria (exigem ambiente)
- Testes ponta-a-ponta em staging (Web + Flutter + Android + iOS).
- Confirmação de CI verde pós-merge e bootstrap 200 pós-redeploy.
- Reprodução de UI dos itens 3, 6 e 2 (console/log de produção).
