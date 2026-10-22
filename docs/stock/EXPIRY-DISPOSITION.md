# Vencimento, destinação pela unidade e conferência por QR

A data física comprovada de cada peça rege a entrega e a reserva. A peça vence depois do último dia de validade, pelo calendário da empresa. CA e cadastro do EPI não alteram essa regra.

Em Estoque → Validade e bloqueios, o painel Estoque bloqueado inclui automaticamente as peças fisicamente vencidas, mesmo quando o status gravado ainda é `in_stock`. A consulta não altera o banco. O botão Desbloquear fica indisponível para vencidos, e o backend também recusa o desbloqueio.

A unidade abre **Destinar peça bloqueada** pelo QR, decide doação, devolução à empresa/fornecedor ou descarte, indica o destinatário sugerido, motivo e referência de envio. Somente a confirmação da retirada física e do envio dá baixa de uma peça no saldo da própria unidade. A doação não autoriza o uso de EPI vencido.

O histórico mostra destinatário, referência de envio, responsável e data. O QR e a peça permanecem registrados em estado terminal. Reenvios idênticos não repetem a baixa; uma destinação diferente sobre a mesma peça é recusada. O saldo, o estado da peça, o movimento e o evento são uma única transação. Não há transferência implícita de saldo para outra unidade.

Ao regularizar peças selecionadas em lote, a fabricação informada é salva no lote e nas peças selecionadas. O tamanho pode ser conferido separadamente por QR, permitindo tamanhos diferentes no mesmo lote físico. Tamanhos já cadastrados são preservados quando não há correção explícita.

O painel **Conferência de fabricação e tamanho** lista peças com dados ausentes ou recuperáveis. A fabricação pode vir do próprio lote vinculado e o tamanho do movimento original exato da peça; nenhum dado é copiado de outro lote ou do catálogo do EPI. A unidade confirma os dados pela etiqueta/documento e pela peça, com evidência e justificativa. Essa correção não altera a validade comprovada, o saldo ou a elegibilidade de peças com validade desconhecida.

A migration numerada 033 inclui o estado terminal `donated` e o evento `donation`, sem alterar permissões de banco nem remover registros. Precisa ser aplicada antes dos novos comandos de destinação.
