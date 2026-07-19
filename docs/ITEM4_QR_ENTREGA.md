# Item 4 — QR híbrido de entrega + fechamento do portal

## Objetivo
O QR ligado à entrega de um EPI **identifica o colaborador** (nome+sobrenome,
matrícula) e a **entrega específica**, sem expor dado pessoal direto. A
conferência mostra colaborador/matrícula/EPI/tamanho/lote/solicitação; ao
confirmar, o ciclo fecha (assinatura + solicitação `entregue`) e o portal do
colaborador passa a exibir **"EPI entregue"**. A etiqueta pode ser reimpressa
(mesma etiqueta) com justificativa + auditoria, **sem** duplicar entrega.

## Modelo híbrido de QR
- **QR do colaborador** (`employee_portal_links.qr_code_value`): identificação
  institucional (portal, consultas). Permanece válido, inalterado.
- **QR da entrega** (`deliveries.handover_token`, novo): token OPACO por
  entrega, gerado na criação da entrega (`generate_handover_token`,
  `ENTREGA-<urlsafe>`). É por ele que se confirma o recebimento.
- Ambos compartilham o mesmo backend e auditoria — sem regra duplicada.

## Banco (aditivo, portável SQLite/PostgreSQL via `_safe_add_column`)
`ensure_delivery_handover_columns` adiciona em `deliveries`:
`handover_token`, `handover_confirmed_at`, `handover_confirmed_by`,
`handover_confirmed_name`, `handover_reprint_count`. Sem colunas destrutivas,
sem PRAGMA.

## API
- `GET /api/deliveries/handover-lookup?code=<token>` → `{ ok, handover }`.
  Projeção **segura** (sem CPF): `employee_first_name`, `employee_last_name`,
  `employee_registration` (matrícula), `epi_name`, `size/glove_size/uniform_size`,
  `lot_code`, `request_id`/`request_status`, `unit_name`, `already_confirmed`.
  Permissão `deliveries:view`; escopo de empresa (master vê todas).
- `POST /api/deliveries/handover-confirm` `{ actor_user_id, code, signature_* }`
  → `{ ok, confirmed, already_confirmed, confirmed_at }`. **Idempotente**:
  segunda chamada não duplica. Marca `handover_confirmed_*`, assina a entrega se
  ainda não assinada e garante a solicitação vinculada como `entregue`.
  Permissão `deliveries:create`; escopo de empresa.
- `POST /api/stock/labels/reprint` (existente): reimprime a MESMA etiqueta
  (mesmo `qr_code_value`), exige `reason`, grava auditoria em
  `epi_stock_item_reprints` e incrementa `reprint_count`. Não cria entrega.

## Segurança
- QR carrega apenas o token opaco; nunca CPF/nome. A resolução exige sessão +
  permissão + mesma empresa (unidade operacional respeitada nos endpoints de
  entrega). Confirmação idempotente evita replay de fechamento.

## Portal
`get_portal_employee_deliveries` passa a expor `handover_confirmed_at`; a
solicitação vira `entregue` e aparece fechada no portal do colaborador.

## Camada compartilhada Flutter (contrato)
`DeliveriesApi.handoverLookup` / `handoverConfirm` espelham o contrato acima,
sem lógica de negócio no app; validadas por teste de contrato.

## Testes
- Backend (SQLite+PG-portável): token opaco/único; projeção segura sem CPF;
  lookup de token inexistente falha; multi-tenant barrado; master irrestrito;
  confirm idempotente + fecha solicitação; estado refletido no lookup.
- Frontend web: wiring da conferência (consumo dos endpoints, sem regra
  duplicada).
- Contrato Flutter: caminho/query/corpo/chaves de resposta.

## Rollback
`git revert`. Mudanças de banco aditivas (colunas com default), sem migração
destrutiva; endpoints e UI isolados.
