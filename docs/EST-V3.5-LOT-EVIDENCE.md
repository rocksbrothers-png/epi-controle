# EST-V3.5 — comprovação de lotes físicos

O mecanismo registra a comprovação no lote físico explicitamente conferido,
com vínculo às peças/QR, responsável, data, justificativa e anexo preservado.
Não cria lotes por coincidência de nome/código nem usa cadastro do EPI ou CA
como autoridade de validade.

## Uso na web

Em **Estoque → Validade e Bloqueios**:

1. Peças que já têm QR: marque em **Pendentes de regularização** somente os
   QRs fisicamente conferidos do mesmo EPI/unidade/lote. Use **Comprovar lote
   das peças selecionadas**; a ação individual também usa esse mecanismo.
2. Informe o lote real, origem (embalagem/etiqueta ou documento do fabricante),
   validade física, referência da comprovação, justificativa e foto/documento.
   Confira a lista de QRs e confirme a conferência física. Não selecione peças
   apenas porque compartilham EPI ou nome de lote.
3. O painel **Lotes físicos e comprovações** lista os registros e oferece
   download autenticado do anexo. Peças não selecionadas continuam pendentes.

Para saldo já registrado sem peças/QR: selecione empresa, unidade e EPI no
estoque e use **Conciliar peças contadas sem QR**. Conte fisicamente as peças
desse lote, informe quantidade (1–100), tamanho observado e a mesma comprovação
acima. Fabricação pode ser informada quando comprovada. A conciliação gera os
QRs e etiquetas sem incrementar o saldo existente. Quantidades que excedem o
saldo ainda sem peças são recusadas. Faça conferências separadas por lote e
tamanho; se o saldo agregado estiver errado, este fluxo não o corrige.

Na entrada manual de novo estoque, a comprovação anexada também fica vinculada
ao lote e às peças recém-recebidas. Esse fluxo aumenta estoque pelo recebimento
normal; não deve ser usado para individualizar um saldo antigo sem QR.

## Contratos e armazenamento

- `POST /api/stock/lots/regularize-validity`: recebe `items[]` com IDs e QRs
  explícitos, `lot_code`, `physical_expiry_date`, `expiry_source`, `evidence`,
  `justification`, `evidence_file` e `physical_lot_confirmed=true`.
- `POST /api/stock/lots/reconcile`: recebe quantidade e tamanho efetivamente
  contados, empresa/unidade/EPI, os campos da comprovação acima e
  `idempotency_key` única. O backend trava o escopo compartilhado, usa
  `unit_balance.reconciliation_delta` e não altera o saldo agregado.
- `GET /api/stock/lots/evidence`: lista até 200 lotes mais recentes do escopo.
  Com `lot_id`, retorna o arquivo para download pelo cliente autenticado.
- `evidence_file` contém `filename`, `mime` e `content_base64`. Limite de 3 MiB;
  PDF, PNG ou JPEG, com extensão, MIME, base64 e assinatura compatíveis. O
  backend calcula SHA-256 e verifica a integridade antes de devolver o arquivo.
- O lote usa `epi_stock_lots` e `epi_stock_items.lot_id`, já existentes.
  O arquivo é guardado uma única vez no evento `lot_evidence` de
  `epi_stock_events`, append-only, com FK do lote e peça. Os demais eventos
  preservam o histórico por peça. Não há arquivo público, URL compartilhável,
  dependência de disco local nem alteração de schema nesta implementação.
- O anexo documenta a declaração do responsável; a validação de formato/hash
  não autentica o fabricante nem interpreta automaticamente a validade.

## Autorização e consistência

Registrar comprovação exige `stock:regularize_validity`, concedida aos perfis
operacionais existentes (Administrador Local/Gestor de EPI), com escopo ativo
de unidade. A conciliação também exige `stock:adjust`. Consulta/download exige
`stock:view` e isolamento de empresa/unidade reaplicado em cada acesso.

Seleção duplicada, QR incorreto, outro EPI/unidade/empresa, lote já identificado
com outro código, estado incompatível ou comprovação incompleta são recusados.
O lote, vínculo das peças, validade, histórico e arquivo pertencem à mesma
transação; qualquer falha desfaz tudo. Lote vencido permanece bloqueado.
Regularização idêntica não duplica lote/anexo; conciliação idêntica com a mesma
chave retorna os mesmos QRs. Concorrência não ultrapassa o saldo sem lastro.

APIs anteriores de regularização individual e recebimento textual mantêm seus
contratos para clientes legados; os formulários web novos exigem o anexo.
Datas de estoque histórico não são preenchidas automaticamente.

## Verificação

`tests_postgres/test_stock_lot_evidence_http.py` exercita API HTTP/JWT real e
PostgreSQL: seleção explícita, peça não selecionada preservada, arquivo único,
download/integridade, imutabilidade nativa, perfis/escopos, formatos recusados,
desconhecido/vencido, idempotência, concorrência e rollback. A conciliação cobre
saldo sem peças, peças já existentes/bloqueadas, limites do delta, QRs sem
incrementar saldo, reenvio e falha de auditoria.

`static/js/test/stock-lot-evidence-runtime.js` executa funções reais da interface
em VM: seleção, modal, comprovação/arquivo obrigatórios, requisição com todos os
QRs, consulta/erro, conciliação e cancelamento. Esses testes não substituem a
validação no navegador do ambiente publicado.

Rollback: reverter os commits e republicar os assets. Os registros de prova já
gravados devem ser preservados como histórico; não apagar arquivos/eventos.
