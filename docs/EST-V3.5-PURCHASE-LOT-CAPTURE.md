# EST-V3.5 — captura de lote na conferência de Compras

## Problema e resultado

A conferência da requisição já tinha câmera e validade por lote. Porém, usava o
OCR de fabricação, que recusa datas futuras; não distinguia fabricação de
validade, descartava a foto e não carregava fabricação para as peças. Também
copiava datas entre linhas do mesmo EPI, sem comprovar identidade física do lote.
A conferência de PO não oferecia a mesma captura na web.

A web Corporate e SaaS passam a usar **Foto / comprovar lote** na conferência
da requisição e da PO. Uma captura por lote reúne identificação física,
fabricação, validade, origem, referência, foto/documento e confirmação do
responsável. O mesmo formulário atende cada lote separado ou uma exceção de
uma peça. Os dados seguem automaticamente para o estoque e as etiquetas,
sem preencher fabricação novamente em Estoque ou regularizar depois as peças
que já chegaram com validade física comprovada.

## Operação

1. Em Compras, registre as quantidades realmente recebidas e abra a conferência.
2. Para um lote único, use **Foto / comprovar lote**. Para lotes diferentes,
   use **Separar em lotes**, informe as quantidades e comprove cada lote.
3. Fotografe a etiqueta ou anexe a foto/documento do fabricante. A foto aparece
   para revisão. Uma imagem PNG/JPEG permite OCR; PDF permite preencher datas
   manualmente. O limite é 3 MiB por anexo.
4. Revise as sugestões de fabricação e validade **separadamente**. Rótulos
   FAB/MFG/PRODUÇÃO e VAL/VALIDADE/EXP/VENCIMENTO guiam a leitura. Datas sem
   rótulo, incompletas, conflitantes ou ambíguas exigem seleção/correção manual.
   Sugestões não substituem campos já preenchidos manualmente. Validade de CA
   identificada como tal não é sugerida como validade física.
5. Confira lote, origem e referência e marque a confirmação física. Registrar
   conferência lança todas as peças, datas e comprovantes na mesma transação.

Fabricação isolada nunca libera estoque nem calcula validade pelo cadastro do
EPI/CA. Se só ela estiver comprovada, deixe validade vazia: fabricação e foto
são preservadas, e as peças ficam pendentes/bloqueadas. OCR indisponível ou
leitura malsucedida mantém a foto para preenchimento manual. Cancelar a captura
não salva arquivo nem altera estoque.

O arquivo é preservado uma vez por lote em `epi_stock_events`, com SHA-256 e
acesso autenticado; cada peça referencia o lote de `epi_stock_lots`. O painel
**Lotes físicos e comprovações** mostra fabricação, validade e permite baixar
a prova, usando o mecanismo de estoque já existente. Não há novo schema,
arquivo público nem armazenamento de dados físicos no catálogo do EPI.

## Contrato e consistência

`received_items[].lots[]` da PR e `items[].lots[]` de `action=checked` da PO
aceitam `capture_version=1`, `quantity`, `lot_code`, `manufacture_date`,
`manufacturer_validity_date`, `expiry_source`, `evidence`, `evidence_file` e
`physical_lot_confirmed=true`. A soma deve corresponder à quantidade recebida
persistida. Capturas aceitam até 10 lotes comprovados, 500 peças e 12 MiB em
anexos no envio, mantendo 3 MiB por arquivo.

`POST /api/purchases/lot-label-ocr` usa autenticação e permissões de atualização
de requisição ou recebimento de PO. Recebe `evidence_file`; retorna sugestões
`manufacture_date`, `physical_expiry_date`, `candidates` e
`review_required=true`. A chamada OCR não grava nada. O processamento preserva
o anexo original e reduz apenas a imagem de trabalho do OCR; aceita até
32 megapixels e limita o maior lado de processamento a 2000 pixels.

Contratos legados permanecem aceitos. Dados de uma linha não preenchem outra
pelo simples fato de compartilharem o EPI. Reenvios e concorrência não duplicam
recebimento; uma requisição e a PO vinculada não podem lançar o mesmo estoque
pelos dois caminhos. Perfis e escopos existentes são reaplicados nos endpoints.
Lote vencido entra bloqueado. Falha na prova/auditoria desfaz todo o recebimento.

Esta entrega cobre a web e os contratos do backend usados por Corporate e SaaS.
As telas Flutter não foram alteradas; seus contratos existentes permanecem.

## Validação

- `tests/test_purchase_lot_capture.py`: datas rotuladas distintas, validade
  futura, ambiguidade, CA, dados inválidos e limites da captura.
- `tests_postgres/test_purchase_lot_capture_http.py`: HTTP/JWT e PostgreSQL
  reais para PR/PO, datas e arquivos por lote, consulta posterior, fabricação
  sem validade, vencidos, rollback e concorrência inclusive entre PR e PO.
- `static/js/test/purchase-lot-capture-runtime.js`: funções reais da web em VM,
  foto única, duas datas, confirmação física, correções manuais, falha/cancelamento
  de OCR, resposta atrasada, captura no payload e ausência de cópia entre EPIs.
- Leitura local com Tesseract em etiqueta sintética FAB/VAL; não utiliza nem
  regulariza documentos ou estoque de produção.

Após merge/publicação, validar a captura no navegador/câmera do sistema real.
Rollback: reverter os commits e republicar os assets, preservando os lotes e
os eventos de comprovação já registrados.
