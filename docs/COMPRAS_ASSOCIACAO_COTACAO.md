# Compras — associação confirmada de linhas de cotação

Decisão de 2026-10-22: **opção C** (confirmação explícita do operador) **combinada com o bloqueio da
opção A** (CA divergente impede a associação). Vale para "Salvar Preços na Requisição" e
"Criar PO a partir do arquivo", nos dois projetos (Corporate e SaaS).

## Regras

| # | Regra | Onde |
|---|---|---|
| 1 | Fornecedor, origem, colaborador e unidade nunca associam sozinhos — não tornam um item candidato | `evaluatePurchaseImportCandidates` e `validate_quote_associations` |
| 2 | CA presente nos dois lados e divergente **bloqueia** (CA comparado só pelos dígitos: `CA 12.345` = `12345`) | cliente (opção desabilitada) e backend (400) |
| 3 | CA ausente: nunca há sugestão automática; o operador escolhe e confirma; o backend exige descrição, modelo ou id do item coincidente | cliente e backend |
| 4 | CA coincidente sozinho não gera sugestão: precisa também de descrição, modelo ou id do item, e de nenhuma divergência (fabricante, tamanho, modelo) | cliente |
| 5 | Todos os candidatos relevantes aparecem com o que coincide e o que diverge; bloqueados aparecem desabilitados com o motivo | prévia |
| 6 | Sugestão só quando é única — inclusive entre linhas; nunca escolhida em silêncio (vem rotulada "sugerido") | cliente |
| 7 | Resumo com associação, preço, quantidade e total; exige marcar "Conferi…" e confirmar | cliente |
| 8 | Backend revalida: confirmação por item, item da requisição e da empresa, EPI da empresa, versão do item (`expected_updated_at`), CA, identidade, item repetido; permissão e escopo de unidade/empresa da rota | `modules/purchases/service.py` |
| 9 | Auditoria `quote_association_confirmed` por item: operador (id, nome, perfil, IP), linha do arquivo, item, preço, quantidade e evidências | `purchase_events` |
| 10 | Preço gravado só no item confirmado; `UPDATE ... AND updated_at = ?` — alteração concorrente rejeita o lote inteiro | `save_purchase_request_prices` |

O arquivo de cotação aceita a coluna opcional **modelo** (`modelo`, `model`, `modelo_referencia`,
`referencia_modelo`, `model_reference`), comparada com `epis.model_reference`.

## Contrato

`POST /api/purchase-requests/{id}/save-prices` — cada item:
`item_id, unit_price, quantity, confirmed: true, expected_updated_at, quote_line, quote_item_id,
quote_epi, quote_ca, quote_manufacturer, quote_model, quote_supplier`.

`POST /api/purchase-orders` com `source: "quote_import"` — os mesmos campos por item (com
`purchase_request_item_id`), e o `epi_id` precisa ser o do item da requisição. PO criada por outros
caminhos (ex.: Flutter) mantém o contrato anterior.

## Testes

- `static/js/test/purchase-quote-import-runtime.js` — executa `views/purchases.js` e o módulo de
  regras reais: CA divergente, CA ausente, fornecedor com item incorreto, múltiplos candidatos,
  confirmação, cancelamento, conferência obrigatória, escolha alterada, alteração concorrente,
  detalhe trocado, módulos ausentes e escape de HTML.
- `tests/test_purchase_save_prices.py` e `tests/test_purchase_quote_association_po.py` — regras do
  backend, tenant, concorrência (versão e corrida entre validação e escrita) e auditoria.
