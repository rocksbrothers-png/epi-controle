'use strict';

// Valores canônicos legados são preservados no payload e na auditoria.
// Este adaptador só fornece o rótulo, no momento da apresentação.
(function () {
  const keys = {
  'Valor acima do esperado': 'purchase.reviewReason.valor_acima_do_esperado',
  'Fornecedor incorreto': 'purchase.reviewReason.fornecedor_incorreto',
  'Item com preço divergente': 'purchase.reviewReason.item_com_preco_divergente',
  'Cotação incompleta': 'purchase.reviewReason.cotacao_incompleta',
  'Necessário novo fornecedor': 'purchase.reviewReason.necessario_novo_fornecedor',
  'Quantidade divergente': 'purchase.reviewReason.quantidade_divergente',
  'Outro': 'outsourcedCompany.kindOther',
  'Acrescentar novos itens': 'purchase.reviewReason.acrescentar_novos_itens',
  'Corrigir item existente': 'purchase.reviewReason.corrigir_item_existente',
  'Revisar quantidade': 'purchase.reviewReason.revisar_quantidade',
  'Reavaliar item inicialmente reprovado': 'purchase.reviewReason.reavaliar_item_inicialmente_reprovado',
  'Justificar necessidade': 'purchase.reviewReason.justificar_necessidade',
  'Anexar informação complementar': 'purchase.reviewReason.anexar_informacao_complementar',
  'Item não necessário': 'purchase.reviewReason.item_nao_necessario',
  'Quantidade incorreta': 'purchase.reviewReason.quantidade_incorreta',
  'Fornecedor inadequado': 'purchase.reviewReason.fornecedor_inadequado',
  'EPI incompatível': 'purchase.reviewReason.epi_incompativel',
  'Fora do escopo da solicitação': 'purchase.reviewReason.fora_do_escopo_da_solicitacao'
};
  function label(value) {
    const key = keys[value];
    return key ? (globalThis.trEpi?.(key, value) ?? value) : value;
  }
  function key(value) { return keys[value] || ''; }
  globalThis.__EPI_PURCHASE_REASON_LABELS__ = Object.freeze({ label, key, keys });
}());
