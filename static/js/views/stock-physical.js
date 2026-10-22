'use strict';

// Formulários recebem o contexto do estoque; nenhuma unidade é escolhida por consolidação.
(function () {
  const escape = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const text = (key, fallback) => typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  const t = (key, fallback) => escape(text(`stock.physical.${key}`, fallback));

  function dialog(options) {
    const { item, kind, context, api, currentContext, refresh } = options;
    if (document.getElementById('stock-physical-dialog')) {return;}
    const disposition = kind === 'disposition';
    const overlay = document.createElement('div');
    overlay.id = 'stock-physical-dialog';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
    const field = (name, label, value = '', type = 'text') => `<label>${t(name, label)}<input name="${name}" type="${type}" value="${escape(value)}" maxlength="${name === 'justification' || name === 'evidence' ? 2000 : 240}" required></label>`;
    overlay.innerHTML = `<form class="card" role="dialog" aria-modal="true" aria-labelledby="stock-physical-title" style="max-width:600px;width:96vw;padding:24px;max-height:92vh;overflow:auto;">
      <h3 id="stock-physical-title">${disposition ? t('dispose', 'Destinar peça bloqueada') : t('correct', 'Conferir fabricação e tamanho')}</h3>
      <p>${escape(item.epi_name)} · ${escape(item.unit_name)}<br><strong>${escape(item.qr_code_value)}</strong> · ${escape(item.lot_code || '—')}</p>
      ${disposition ? `<label>${t('action', 'Destinação decidida pela unidade')}<select name="action"><option value="donation">${t('donation', 'Doação')}</option><option value="supplier_return">${t('supplier_return', 'Devolução à empresa / fornecedor')}</option><option value="discard">${t('discard', 'Descarte')}</option></select></label>
        <p class="hint">${t('donationHint', 'A doação registra a saída para o destinatário indicado pela unidade. Peça vencida continua identificada como vencida e não é liberada para uso como EPI.')}</p>
        ${field('recipient', 'Destinatário sugerido pela unidade')}
        <label>${t('recipient_reference', 'CNPJ / contato / endereço do destinatário (opcional)')}<input name="recipient_reference" maxlength="240"></label>
        ${field('shipment_reference', 'Comprovante / referência de envio')}`
        : `${field('manufacture_date', 'Fabricação comprovada do lote', item.manufacture_date || '', 'date')}
        ${field('size', 'Tamanho fisicamente conferido', item.size === 'N/A' ? '' : item.size || '')}
        ${field('evidence', 'Etiqueta / documento do fabricante conferido')}`}
      ${field('justification', 'Motivo / justificativa')}
      <label style="display:flex;gap:8px;align-items:start;"><input name="confirmed" type="checkbox" style="width:auto;min-width:0;" required>${disposition ? t('confirmShipment', 'Confirmo a retirada física e o envio ao destinatário informado. A peça será baixada do estoque da unidade.') : t('confirmMetadata', 'Conferi a peça pelo QR, o tamanho e a fabricação na etiqueta/documento do lote.')}</label>
      <p class="hint" id="stock-physical-error" role="alert"></p>
      <div class="action-group"><button type="button" id="stock-physical-cancel" class="ghost">${t('cancel', 'Cancelar')}</button><button type="submit">${disposition ? t('submitShipment', 'Confirmar envio e baixar estoque') : t('submitMetadata', 'Salvar conferência')}</button></div>
    </form>`;
    document.body.appendChild(overlay);
    const form = overlay.querySelector('form');
    const submit = form.querySelector('[type="submit"]');
    const cancel = overlay.querySelector('#stock-physical-cancel');
    let busy = false;
    cancel.addEventListener('click', () => { if (!busy) {overlay.remove();} });
    overlay.addEventListener('click', (event) => { if (event.target === overlay && !busy) {overlay.remove();} });
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (busy || !form.reportValidity()) {return;}
      const now = currentContext();
      const error = overlay.querySelector('#stock-physical-error');
      if (String(now.companyId) !== String(context.companyId) || String(now.unitId) !== String(context.unitId)) {
        error.textContent = text('stock.physical.contextChanged', 'A empresa/unidade mudou. Feche e abra novamente a conferência.');
        return;
      }
      const values = Object.fromEntries(new FormData(form));
      const body = { ...values, stock_item_id: Number(item.id), qr_code: item.qr_code_value,
        company_id: Number(context.companyId), unit_id: Number(item.unit_id) };
      if (disposition) {body.shipment_confirmed = true;}
      else {
        body.physical_confirmed = true;
        body.glove_size = item.glove_size && item.glove_size !== 'N/A' ? values.size : 'N/A';
        body.uniform_size = item.uniform_size && item.uniform_size !== 'N/A' ? values.size : 'N/A';
      }
      busy = true; submit.disabled = true; cancel.disabled = true;
      error.textContent = text('stock.loading', 'Processando...');
      try {
        await api(`/api/stock/items/${disposition ? 'disposition' : 'physical-metadata'}`, { method: 'POST', body: JSON.stringify(body) });
        overlay.remove();
        await refresh();
      } catch (failure) {
        error.textContent = failure.message || text('stock.physical.failed', 'Não foi possível registrar a ação.');
      } finally { busy = false; submit.disabled = false; cancel.disabled = false; }
    });
  }

  globalThis.__EPI_STOCK_PHYSICAL__ = { dialog };
}());
