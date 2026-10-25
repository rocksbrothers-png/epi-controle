# Compras — associação confirmada de linhas de cotação

Decisão de 2026-10-22: **opção C** (confirmação explícita do operador) **combinada com o bloqueio da
opção A** (CA divergente impede a associação). Vale para "Salvar Preços na Requisição" e
"Criar PO a partir do arquivo", nos dois projetos (Corporate e SaaS).

## Regras

| # | Regra | Onde |
|---|---|---|
| 1 | Fornecedor, origem, colaborador e unidade nunca associam sozinhos — não tornam um item candidato | `evaluatePurchaseImportCandidates` e `validate_quote_associations` |
| 2 | CA presente nos dois lados e divergente **bloqueia** (CA comparado só pelos dígitos: `CA 12.345` = `12345`) | cliente (opção desabilitada) e backend (400) |
| 3 | CA ausente: nunca há sugestão automática; o operador escolhe e confirma; o backend exige identificação inequívoca (descrição igual, modelo igual ou id do item) | cliente e backend |
| 4 | CA coincidente sozinho não identifica: precisa também de descrição igual, modelo igual ou id do item. Qualquer contradição (descrição ou fabricante diferente, modelo diferente/parcial, tamanho diferente) bloqueia a associação mesmo com CA igual; descrição parcial nunca conta como identidade. O CA atual do catálogo prevalece sobre o snapshot do item | cliente e backend |
| 5 | Todos os candidatos relevantes aparecem com o que coincide e o que diverge; bloqueados aparecem desabilitados com o motivo | prévia |
| 6 | Sugestão só quando é única — inclusive entre linhas; nunca escolhida em silêncio (vem rotulada "sugerido") | cliente |
| 7 | Resumo com associação, preço, quantidade e total; exige marcar "Conferi…" e confirmar | cliente |
| 8 | Backend revalida: confirmação por item, item da requisição e da empresa, EPI da empresa, versão do item (`expected_updated_at`), CA, identidade, item repetido; permissão e escopo de unidade/empresa da rota | `modules/purchases/service.py` |
| 9 | Auditoria `quote_association_confirmed` por item: operador (id, nome, perfil, IP), linha do arquivo, item, preço, quantidade e evidências | `purchase_events` |
| 10 | Preço gravado só no item confirmado, igual ao preço e à quantidade da linha assinada; `UPDATE ... AND updated_at = ?` e mudança de situação da requisição condicionada — alteração concorrente rejeita o lote inteiro. Itens já aprovados não mudam e são informados ao operador | `save_purchase_request_prices` |

### Integridade da linha do arquivo

`POST /api/purchase-quote-file/parse` assina cada linha processada (`quote_issued_at`, `quote_sig`):
HMAC-SHA256 com chave derivada de `JWT_SECRET`, vinculando empresa, usuário, horário e os campos da
linha. Ao salvar ou criar a PO, o backend recusa linha sem assinatura, alterada (ex.: CA apagado,
preço trocado), de outro usuário/empresa ou com mais de 24 horas — o operador visualiza o arquivo
de novo. Assim as regras 2–4 valem sobre o que o arquivo realmente diz, não sobre o que o navegador
enviou.

### PO a partir do arquivo

Além das regras acima: requisição obrigatória; requisição que já tem PO vinculada é recusada; o
vínculo é gravado com `WHERE linked_po_id IS NULL` (duas criações simultâneas não geram duas POs);
nome, CA e fabricante gravados na PO vêm do catálogo, não do texto do arquivo; preço e quantidade
são os validados contra a linha assinada; tamanhos, unidade de medida, origem e colaborador vêm do
item da requisição.

Quantidade ausente ou ilegível no arquivo fica em branco na linha (não vira "1"): a associação
usa a quantidade do item da requisição.

### Limites conhecidos (fora do escopo desta decisão)

- PO criada por outros caminhos (sem `source: "quote_import"`, ex.: Flutter) não passa por estas
  regras nem pela proteção de vínculo duplo — mantém o contrato anterior.
- A assinatura vincula empresa, usuário e horário, não a requisição: a mesma linha pode ser
  apresentada a outra requisição da empresa em 24 h, onde as regras de identidade valem de novo.
  A assinatura impede alteração no navegador; não valida o conteúdo que o próprio operador enviou.

O arquivo de cotação aceita a coluna opcional **modelo** (`modelo`, `model`, `modelo_referencia`,
`referencia_modelo`, `model_reference`), comparada com `epis.model_reference`.

## Contrato

`POST /api/purchase-requests/{id}/save-prices` — cada item:
`item_id, unit_price, quantity, confirmed: true, expected_updated_at, quote_line, quote_item_id,
quote_epi, quote_ca, quote_manufacturer, quote_model, quote_supplier, quote_size, quote_glove_size,
quote_uniform_size, quote_qty, quote_unit_price, quote_issued_at, quote_sig`. Resposta:
`affected_item_ids`.

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
