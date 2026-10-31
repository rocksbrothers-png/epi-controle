(function () {
  'use strict';
  const token = window.location.pathname.split('/').filter(Boolean).pop();
  const transport = globalThis.__EPI_SUPPLIER_PORTAL_API__;
  let dados = null;

  function el(id) { return document.getElementById(id); }
  function t(key, vars) { return globalThis.EpiI18n.t('supplierPortal.' + key, vars); }
  function label(id, key, vars, refs) {
    const node = el(id);
    node.textContent = globalThis.EpiI18n.textFor(node, 'supplierPortal.' + key, t(key,vars), vars, refs);
  }
  function bound(key, vars, refs) { return globalThis.EpiI18n.bindText('supplierPortal.'+key, vars, t(key,vars), refs); }
  function number(value) { return bound('value',{value:value},{value:{type:'number',value:value}}); }
  function date(value) { return bound('value',{value:value},{value:{type:'date',value:value}}); }
  function measure(value, count) {
    const key = ({unidade:'unit',un:'unit',par:'pair'})[value];
    return key ? globalThis.EpiI18n.bindText('operationalAlerts.measure.'+key,{count:count},value) : esc(value);
  }
  function status(value) {
    const key = 'supplierPortal.status.'+value, translated = globalThis.EpiI18n.t(key);
    return translated === key ? esc(value) : globalThis.EpiI18n.bindText(key,{},translated);
  }
  function feedbackError(id, payload, fallbackKey) {
    const node = el(id), detail = globalThis.EpiI18n.describeApiError(payload,t(fallbackKey));
    if (detail.key) {node.textContent = globalThis.EpiI18n.textFor(node,detail.key,detail.text,detail.vars,detail.refs);}
    else {globalThis.EpiI18n.clearBinding(node);node.textContent=detail.text;}
  }
  function inputLabels(q) {
    q.items.forEach((item,index) => {
      [['preco-','itemPrice'],['prazo-','itemLead'],['recusa-','itemDecline']].forEach((pair) => {
        const node=el(pair[0]+index), vars={item:item.epi_name};
        node.setAttribute('aria-label',globalThis.EpiI18n.attributeFor(node,'aria-label','supplierPortal.'+pair[1],t(pair[1],vars),vars));
      });
    });
  }

  function falha(mensagem) {
    el('conteudo').style.display = 'none';
    el('painel-erro').style.display = 'block';
    label('texto-erro',mensagem);
    label('subtitulo','accessUnavailable');
  }
  function moeda(v) { return bound('value',{value:Number(v||0)},{value:{type:'number',value:Number(v||0),options:{style:'currency',currency:'BRL'}}}); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function renderCotacao(q) {
    label('subtitulo','quoteHeading',{company:dados.company_name,id:q.id,supplier:dados.supplier_name});
    const jaRespondida = q.status !== 'draft' && q.status !== 'sent';
    let html = '<h2 data-i18n="supplierPortal.requestedItems">Itens solicitados' + (jaRespondida ? '<span class="tag" data-i18n="supplierPortal.answered">já respondida</span>' : '') + '</h2>';
    html += '<div class="table-scroll"><table><thead><tr><th data-i18n="supplierPortal.item">Item</th><th class="esconde-mobile" data-i18n="supplierPortal.ca">CA</th><th data-i18n="supplierPortal.quantity">Qtde</th><th data-i18n="supplierPortal.unitPriceBrl">Preço unit. (R$)</th><th data-i18n="supplierPortal.leadDays">Prazo (dias)</th><th data-i18n="supplierPortal.decline">Recusar</th></tr></thead><tbody>';
    q.items.forEach((item, indice) => {
      html += '<tr>' +
        '<td>' + esc(item.epi_name) + '</td>' +
        '<td class="esconde-mobile">' + esc(item.ca || '-') + '</td>' +
        '<td>' + number(item.quantity_requested) + ' ' + measure(item.unit_measure,item.quantity_requested) + '</td>' +
        '<td><input type="number" min="0" step="0.01" id="preco-' + indice + '" value="' + (item.unit_price || '') + '"' + (jaRespondida ? ' disabled' : '') + '></td>' +
        '<td><input type="number" min="0" step="1" id="prazo-' + indice + '" value="' + (item.lead_time_days || '') + '"' + (jaRespondida ? ' disabled' : '') + '></td>' +
        '<td style="text-align:center"><input type="checkbox" id="recusa-' + indice + '"' + (item.declined ? ' checked' : '') + (jaRespondida ? ' disabled' : '') + '></td>' +
        '</tr>';
    });
    html += '</tbody></table></div>';
    html += '<div class="row">' +
      '<div><label for="frete" data-i18n="supplierPortal.freightBrl">Frete (R$)</label><input type="number" min="0" step="0.01" id="frete" value="' + (q.freight_value || '') + '"' + (jaRespondida ? ' disabled' : '') + '></div>' +
      '<div><label for="pagamento" data-i18n="supplierPortal.paymentTerms">Condições de pagamento</label><input type="text" id="pagamento" value="' + esc(q.payment_terms) + '"' + (jaRespondida ? ' disabled' : '') + '></div>' +
      '</div>' +
      '<div class="row"><div><label for="observacoes" data-i18n="supplierPortal.notes">Observações</label><textarea id="observacoes" rows="2"' + (jaRespondida ? ' disabled' : '') + '>' + esc(q.notes) + '</textarea></div></div>' +
      '<div class="row"><div><label id="proposal-caption" for="proposta" data-i18n="supplierPortal.proposal">Anexar proposta (PDF/JPG/PNG, até 5 MB)</label><input type="file" hidden id="proposta" accept="application/pdf,image/jpeg,image/png"' + (jaRespondida ? ' disabled' : '') + '><button class="file-picker" type="button" id="pick-proposal" aria-labelledby="proposal-caption pick-proposal" aria-describedby="proposal-name" data-i18n="supplierPortal.chooseFile"' + (jaRespondida ? ' disabled' : '') + '>Escolher arquivo</button> <span id="proposal-name" data-i18n="supplierPortal.noFile">Nenhum arquivo selecionado</span></div></div>';
    if (!jaRespondida) {
      html += '<button id="enviar" data-i18n="supplierPortal.sendQuote">Enviar cotação</button>';
    }
    html += '<p class="msg" id="mensagem"></p>';
    el('conteudo').innerHTML = html;
    el('conteudo').style.display = 'block';
    inputLabels(q);
    el('pick-proposal').addEventListener('click', () => el('proposta').click());
    el('proposta').addEventListener('change', () => {
      const file=el('proposta').files[0], name=el('proposal-name');
      if (file) {globalThis.EpiI18n.clearBinding(name);name.textContent=file.name;}
      else {label('proposal-name','noFile');}
    });
    if (jaRespondida) { return; }
    el('enviar').addEventListener('click', () => { enviarCotacao(q); });
  }

  function enviarCotacao(q) {
    const itens = [];
    for (let i = 0; i < q.items.length; i++) {
      itens.push({
        quote_item_id: q.items[i].quote_item_id,
        unit_price: parseFloat(el('preco-' + i).value || '0'),
        lead_time_days: parseInt(el('prazo-' + i).value || '0', 10),
        declined: el('recusa-' + i).checked
      });
    }
    const corpo = {
      items: itens,
      freight_value: parseFloat(el('frete').value || '0'),
      payment_terms: el('pagamento').value,
      notes: el('observacoes').value
    };
    const arquivo = el('proposta').files[0];
    const botao = el('enviar');
    botao.disabled = true;
    function postar() {
      transport.answer(token,corpo,globalThis.EpiI18n.lang).then((resposta) => { return resposta.json().then((j) => { return { ok: resposta.ok, json: j }; }); })
        .then((resultado) => {
          const caixa = el('mensagem');
          if (resultado.ok) {
            caixa.className = 'msg ok';
            label('mensagem','quoteSent');
            setTimeout(() => { window.location.reload(); }, 1500);
          } else {
            caixa.className = 'msg erro';
            feedbackError('mensagem',resultado.json,'sendFailed');
            botao.disabled = false;
          }
        })
        .catch(() => {
          el('mensagem').className = 'msg erro';
          label('mensagem','connectionFailed');
          botao.disabled = false;
        });
    }
    if (arquivo) {
      if (arquivo.size > 5 * 1024 * 1024) {
        el('mensagem').className = 'msg erro';
        label('mensagem','proposalTooLarge');
        botao.disabled = false;
        return;
      }
      const leitor = new FileReader();
      leitor.onload = function () {
        corpo.proposal = { file_name: arquivo.name, file_type: arquivo.type, content_base64: leitor.result };
        postar();
      };
      leitor.readAsDataURL(arquivo);
    } else {
      postar();
    }
  }

  function renderPedido(po) {
    label('subtitulo','orderHeading',{company:dados.company_name,id:po.po_number || ('#'+po.id),supplier:dados.supplier_name});
    let html = '<h2 data-i18n="supplierPortal.orderItems">Itens do pedido</h2>';
    html += '<div class="table-scroll"><table><thead><tr><th data-i18n="supplierPortal.item">Item</th><th class="esconde-mobile" data-i18n="supplierPortal.ca">CA</th><th data-i18n="supplierPortal.quantity">Qtde</th><th data-i18n="supplierPortal.unitPrice">Preço unit.</th></tr></thead><tbody>';
    po.items.forEach((item) => {
      html += '<tr><td>' + esc(item.epi_name) + '</td><td class="esconde-mobile">' + esc(item.ca || '-') + '</td>' +
        '<td>' + number(item.quantity) + '</td><td>' + moeda(item.unit_price) + '</td></tr>';
    });
    html += '</tbody></table></div>';
    if (po.supplier_confirmation_status) {
      html += '<p class="muted" style="margin-top:8px"><span data-i18n="supplierPortal.currentStatus">Situação atual:</span> <strong>' + status(po.supplier_confirmation_status) + '</strong></p>';
    }
    html += '<h2 data-i18n="supplierPortal.recordResponse">Registrar retorno</h2>' +
      '<div class="row">' +
      '<div><label for="acao" data-i18n="supplierPortal.action">Ação</label><select id="acao">' +
      '<option value="confirmed" data-i18n="supplierPortal.confirmOrder">Confirmar pedido</option>' +
      '<option value="delivery_update" data-i18n="supplierPortal.updateDelivery">Atualizar entrega</option>' +
      '<option value="rejected" data-i18n="supplierPortal.rejectOrder">Recusar pedido</option>' +
      '</select></div>' +
      '<div><label for="previsao" data-i18n="supplierPortal.forecast">Previsão de entrega</label><input type="date" id="previsao" value="' + esc(po.expected_delivery_date) + '"></div>' +
      '</div>' +
      '<div class="row">' +
      '<div><label for="transportadora" data-i18n="supplierPortal.carrier">Transportadora</label><input type="text" id="transportadora"></div>' +
      '<div><label for="rastreio" data-i18n="supplierPortal.tracking">Código de rastreio</label><input type="text" id="rastreio"></div>' +
      '</div>' +
      '<div class="row"><div><label for="comentario" data-i18n="supplierPortal.comment">Comentário</label><textarea id="comentario" rows="2"></textarea></div></div>' +
      '<button id="registrar" data-i18n="supplierPortal.record">Registrar</button>' +
      '<p class="msg" id="mensagem"></p>';
    if (po.confirmations.length) {
      html += '<h2 data-i18n="supplierPortal.history">Histórico</h2><div class="table-scroll"><table><thead><tr><th data-i18n="supplierPortal.date">Data</th><th data-i18n="supplierPortal.action">Ação</th><th class="esconde-mobile" data-i18n="supplierPortal.details">Detalhes</th></tr></thead><tbody>';
      po.confirmations.forEach((c) => {
        html += '<tr><td>' + date(String(c.created_at).slice(0, 10)) + '</td><td>' + status(c.status) + '</td>' +
          '<td class="esconde-mobile">' + esc([c.carrier, c.tracking_code, c.comment].filter(Boolean).join(' — ')) + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }
    el('conteudo').innerHTML = html;
    el('conteudo').style.display = 'block';
    el('registrar').addEventListener('click', () => {
      const botao = el('registrar');
      botao.disabled = true;
      transport.confirm(token,{
          status: el('acao').value,
          delivery_forecast: el('previsao').value,
          carrier: el('transportadora').value,
          tracking_code: el('rastreio').value,
          comment: el('comentario').value
        },globalThis.EpiI18n.lang).then((resposta) => { return resposta.json().then((j) => { return { ok: resposta.ok, json: j }; }); })
        .then((resultado) => {
          const caixa = el('mensagem');
          if (resultado.ok) {
            caixa.className = 'msg ok';
            label('mensagem','recorded');
            setTimeout(() => { window.location.reload(); }, 1500);
          } else {
            caixa.className = 'msg erro';
            feedbackError('mensagem',resultado.json,'recordFailed');
            botao.disabled = false;
          }
        })
        .catch(() => {
          el('mensagem').className = 'msg erro';
          label('mensagem','connectionFailed');
          botao.disabled = false;
        });
    });
  }

  function load() {return transport.data(token,globalThis.EpiI18n.lang)
    .then((resposta) => {
      if (!resposta.ok) { throw new Error('denied'); }
      return resposta.json();
    })
    .then((json) => {
      dados = json.item;
      if (dados.entity_type === 'quote') { renderCotacao(dados.quote); }
      else { renderPedido(dados.purchase_order); }
    })
    .catch(() => {
      falha('invalidLink');
    });}
  const selector=el('portal-language');
  const requested=new URLSearchParams(window.location.search).get('lang') || globalThis.EpiI18n.detectBrowserLang();
  const locale=globalThis.EpiI18n.SUPPORTED.find((code) =>{return code.toLowerCase()===String(requested).toLowerCase();})
    || ({pt:'pt-BR',en:'en-GB',es:'es-ES',fr:'fr-FR',nb:'nb-NO',no:'nb-NO'})[String(requested).toLowerCase()] || 'pt-BR';
  function languageState() {
    selector.value=globalThis.EpiI18n.lang;
    const location=new URL(window.location.href);
    location.searchParams.set('lang',globalThis.EpiI18n.lang);
    window.history.replaceState(window.history.state,'',location);
    const notice=el('locale-error');notice.hidden=!globalThis.EpiI18n.loadError;
    if (!notice.hidden) {notice.textContent=globalThis.EpiI18n.textFor(notice,'i18n.languageLoadFailed','Não foi possível carregar o idioma. Tente novamente.');}
  }
  selector.addEventListener('change',() =>{globalThis.EpiI18n.setLang(selector.value,{persist:false}).then(languageState);});
  window.addEventListener('epi:langchange',languageState);
  globalThis.EpiI18n.setLang(locale,{persist:false}).then(() =>{languageState();return load();});
})();
