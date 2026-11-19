'use strict';
/* global tr, escapeHtml */

// UBX Compras P1 — apresentação de status de Compras extraída do app.js, corpos idênticos.
// Os rótulos continuam getters (a troca de idioma vale sem recriar os mapas).
// buildPoStepper e purchaseStatusBadge preservam as globais legadas (eram globais
// pelo Annex B no app.js). Os mapas eram de bloco: ficam só no namespace, e o app.js
// guarda um alias por referência. views/purchases.js (modal do requisitante) também lê
// ITEM_STATUS_LABELS pelo namespace; os mapas não são publicados no globalThis.
// SEC-COMPRAS-1: o rótulo do badge (status + extra, que pode trazer postponed_until
// do servidor via tr sem escape) é texto: passa pelo escapeHtml oficial de
// views/view-helpers.js, carregado antes deste módulo. A marcação do <span> é do componente.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_STATUS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_STATUS_UI_LOADED__ = true;

  const PURCHASE_STATUS_LABELS = {
    get draft() { return (tr('purchase.poStatus.draft', 'Rascunho', {})); }, get open() { return (tr('ui.compras.aberta_262ff7', 'Aberta', {})); }, get sent_to_buyer() { return (tr('ui.app.c_comprador_f09eb8', 'C/ Comprador', {})); }, get quoted() { return (tr('ui.compras.cotada_8912bb', 'Cotada', {})); },
    get pending_approval() { return (tr('ui.compras.cotacao_enviada_ao_aprovador_fcb0ad', 'Cotação Enviada ao Aprovador', {})); }, get partially_approved() { return (tr('ui.app.aprov_parcial_252007', 'Aprov. Parcial', {})); },
    get waiting_buyer_correction() { return (tr('ui.compras.aguardando_correcao_do_comprador_47cb4a', 'Aguardando Correção do Comprador', {})); }, get buyer_resubmitted() { return (tr('ui.compras.reenviada_pelo_comprador_f5a7ee', 'Reenviada pelo Comprador', {})); },
    get waiting_requester_correction() { return (tr('ui.compras.aguardando_correcao_do_requisitante_e61838', 'Aguardando Correção do Requisitante', {})); }, get requester_resubmitted() { return (tr('ui.app.reenviada_pelo_requisitante_129ae0', 'Reenviada pelo Requisitante', {})); },
    get approved() { return (tr('purchase.poStatus.approved', 'Aprovada', {})); }, get rejected() { return (tr('purchase.poStatus.rejected', 'Reprovada', {})); }, get postponed() { return (tr('purchase.poStatus.postponed', 'Prorrogada', {})); },
    get returned_to_buyer() { return (tr('ui.app.retornado_ao_comprador_4ae6e5', 'Retornado ao Comprador', {})); },
    get po_generated() { return (tr('ui.compras.po_gerada_1e0e23', 'PO Gerada', {})); }, get received_partial() { return (tr('purchase.poStatus.received_partial', 'Recebida Parcialmente', {})); }, get received() { return (tr('ui.app.recebida_totalmente_b8cfb4', 'Recebida Totalmente', {})); }, get not_received() { return (tr('ui.app.item_nao_recebido_abb764', 'Item Não Recebido', {})); }, get pending_receipt() { return (tr('ui.app.pendente_de_recebimento_7e1806', 'Pendente de Recebimento', {})); }, get checked() { return (tr('purchase.poStatus.checked', 'Conferida', {})); },
    get closed() { return (tr('purchase.poStatus.closed', 'Fechada', {})); }, get cancelled() { return (tr('ui.compras.cancelada_3d15e6', 'Cancelada', {})); }
  };
  const ITEM_STATUS_LABELS = {
    get open() { return (tr('ui.app.aberto_84276c', 'Aberto', {})); }, get included_in_request() { return (tr('portal.statusInRequest', 'Em Requisição', {})); }, get sent_to_buyer() { return (tr('ui.app.c_comprador_f09eb8', 'C/ Comprador', {})); },
    get quoted() { return (tr('ui.app.cotado_8f67a8', 'Cotado', {})); }, get pending_approval() { return (tr('ui.app.aguard_aprov_f0259c', 'Aguard. Aprov.', {})); }, get approved() { return (tr('portal.statusApproved', 'Aprovado', {})); },
    get partially_approved() { return (tr('ui.app.aprov_parcial_252007', 'Aprov. Parcial', {})); }, get rejected() { return (tr('purchase.status.rejected', 'Rejeitado', {})); }, get ordered() { return (tr('ui.app.pedido_9e9ea5', 'Pedido', {})); },
    get received_partial() { return (tr('ui.app.recebido_parcial_c28671', 'Recebido Parcial', {})); }, get not_received() { return (tr('purchase.poStatus.not_received', 'Não Recebido', {})); }, get received() { return (tr('portal.statusReceived', 'Recebido', {})); }, get checked() { return (tr('ui.app.conferido_113f18', 'Conferido', {})); }, get closed() { return (tr('portal.periodClosed', 'Fechado', {})); },
    get waiting_quote() { return (tr('ui.app.aguardando_cotacao_c58378', 'Aguardando Cotação', {})); }, get waiting_admin_review() { return (tr('purchase.poStatus.waiting_admin_review', 'Em Compra', {})); }
  };

  // P1-5 — etapas canônicas do recebimento da PO e mapeamento a partir do status.
  const PO_STEPPER_STEPS = [
    { get label() { return (tr('purchase.poStep.ordered', 'Pedido', {})); } },
    { get label() { return (tr('portal.statusReceived', 'Recebido', {})); } },
    { get label() { return (tr('ui.app.conferido_113f18', 'Conferido', {})); } },
    { get label() { return (tr('portal.periodClosed', 'Fechado', {})); } }
  ];
  const PO_STEP_INDEX = {
    open: 0, sent_to_buyer: 0, quoted: 0, waiting_quote: 0, waiting_admin_review: 0,
    pending_approval: 0, postponed: 0, approved: 0, partially_approved: 0, ordered: 0,
    received_partial: 1, received: 1, not_received: 1,
    checked: 2,
    closed: 3
  };
  function buildPoStepper(status) {
    if (status === 'rejected') { return ''; } // fluxo terminal sem recebimento
    const idx = Object.prototype.hasOwnProperty.call(PO_STEP_INDEX, status) ? PO_STEP_INDEX[status] : 0;
    return globalThis.dsStepper(PO_STEPPER_STEPS, idx);
  }

  function purchaseStatusBadge(status, extra = '') {
    const colors = { approved: 'green', closed: 'green', received: 'green', received_partial: 'orange', checked: 'green', rejected: 'red', cancelled: 'red', pending_approval: 'orange', partially_approved: 'orange', postponed: 'orange', waiting_buyer_correction: 'orange', waiting_requester_correction: 'orange', buyer_resubmitted: 'orange', requester_resubmitted: 'orange' };
    const c = colors[status] || 'gray';
    const label = (PURCHASE_STATUS_LABELS[status] || status) + (extra ? ` — ${extra}` : '');
    return `<span class="status-chip" style="background:var(--color-${c === 'gray' ? 'bg-alt' : c === 'green' ? 'success-bg' : c === 'red' ? 'danger-bg' : 'warning-bg'});color:var(--color-${c === 'gray' ? 'text-muted' : c === 'green' ? 'success' : c === 'red' ? 'danger' : 'warning'})">${escapeHtml(label)}</span>`;
  }

  globalThis.buildPoStepper = buildPoStepper;
  globalThis.purchaseStatusBadge = purchaseStatusBadge;
  globalThis.__EPI_PURCHASE_STATUS_UI__ = Object.freeze({
    PURCHASE_STATUS_LABELS, ITEM_STATUS_LABELS, PO_STEPPER_STEPS, PO_STEP_INDEX, buildPoStepper, purchaseStatusBadge
  });
})();
