"""Página pública do Portal do Fornecedor (HTML autocontido, sem dependências).

Servida em GET /fornecedor/<token>. O JS embutido consome apenas os endpoints
públicos /api/portal/supplier/<token>/* — nenhum dado além do escopo do token.
Responsiva (o fornecedor abre no celular) e sem frameworks, no espírito do
frontend legado.
"""

PORTAL_PAGE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Portal do Fornecedor — EPI Controle</title>
<style>
  :root { --azul: #1c4e80; --cinza: #f4f6f8; --borda: #d7dde3; --ok: #1e7d46; --erro: #b3261e; }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
  body { background: var(--cinza); color: #1e2833; padding: 16px; }
  .card { max-width: 760px; margin: 0 auto 16px; background: #fff; border: 1px solid var(--borda); border-radius: 10px; padding: 20px; }
  h1 { font-size: 1.25rem; color: var(--azul); margin-bottom: 4px; }
  h2 { font-size: 1rem; margin: 16px 0 8px; }
  .muted { color: #5b6875; font-size: .85rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: .9rem; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--borda); vertical-align: middle; }
  th { color: #40505f; font-weight: 600; font-size: .8rem; text-transform: uppercase; }
  input, select, textarea { width: 100%; padding: 8px; border: 1px solid var(--borda); border-radius: 6px; font-size: .9rem; }
  input[type="checkbox"] { width: auto; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
  .row > div { flex: 1 1 160px; }
  label { display: block; font-size: .8rem; color: #40505f; margin-bottom: 4px; }
  button { background: var(--azul); color: #fff; border: 0; border-radius: 8px; padding: 12px 20px; font-size: 1rem; cursor: pointer; margin-top: 16px; }
  button:disabled { opacity: .5; cursor: default; }
  .msg { margin-top: 12px; padding: 10px 12px; border-radius: 8px; display: none; font-size: .9rem; }
  .msg.ok { display: block; background: #e6f4ec; color: var(--ok); }
  .msg.erro { display: block; background: #fdeceb; color: var(--erro); }
  .tag { display: inline-block; background: #e8eef5; color: var(--azul); border-radius: 999px; padding: 2px 10px; font-size: .75rem; margin-left: 6px; }
  @media (max-width: 560px) { .esconde-mobile { display: none; } td, th { padding: 6px 4px; } }
</style>
</head>
<body>
<div class="card" id="cabecalho">
  <h1>Portal do Fornecedor</h1>
  <p class="muted" id="subtitulo">Carregando…</p>
</div>
<div class="card" id="conteudo" style="display:none"></div>
<div class="card" id="painel-erro" style="display:none">
  <p class="msg erro" style="display:block" id="texto-erro"></p>
</div>
<script>
(function () {
  'use strict';
  var token = window.location.pathname.split('/').filter(Boolean).pop();
  var api = '/api/portal/supplier/' + encodeURIComponent(token);
  var dados = null;

  function el(id) { return document.getElementById(id); }
  function falha(mensagem) {
    el('conteudo').style.display = 'none';
    el('painel-erro').style.display = 'block';
    el('texto-erro').textContent = mensagem;
    el('subtitulo').textContent = 'Acesso indisponível';
  }
  function moeda(v) { return 'R$ ' + Number(v || 0).toFixed(2).replace('.', ','); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function renderCotacao(q) {
    el('subtitulo').textContent = dados.company_name + ' — Cotação #' + q.id + ' para ' + dados.supplier_name;
    var jaRespondida = q.status !== 'draft' && q.status !== 'sent';
    var html = '<h2>Itens solicitados' + (jaRespondida ? '<span class="tag">já respondida</span>' : '') + '</h2>';
    html += '<table><thead><tr><th>Item</th><th class="esconde-mobile">CA</th><th>Qtde</th><th>Preço unit. (R$)</th><th>Prazo (dias)</th><th>Recusar</th></tr></thead><tbody>';
    q.items.forEach(function (item, indice) {
      html += '<tr>' +
        '<td>' + esc(item.epi_name) + '</td>' +
        '<td class="esconde-mobile">' + esc(item.ca || '-') + '</td>' +
        '<td>' + item.quantity_requested + ' ' + esc(item.unit_measure) + '</td>' +
        '<td><input type="number" min="0" step="0.01" id="preco-' + indice + '" value="' + (item.unit_price || '') + '"' + (jaRespondida ? ' disabled' : '') + '></td>' +
        '<td><input type="number" min="0" step="1" id="prazo-' + indice + '" value="' + (item.lead_time_days || '') + '"' + (jaRespondida ? ' disabled' : '') + '></td>' +
        '<td style="text-align:center"><input type="checkbox" id="recusa-' + indice + '"' + (item.declined ? ' checked' : '') + (jaRespondida ? ' disabled' : '') + '></td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    html += '<div class="row">' +
      '<div><label>Frete (R$)</label><input type="number" min="0" step="0.01" id="frete" value="' + (q.freight_value || '') + '"' + (jaRespondida ? ' disabled' : '') + '></div>' +
      '<div><label>Condições de pagamento</label><input type="text" id="pagamento" value="' + esc(q.payment_terms) + '"' + (jaRespondida ? ' disabled' : '') + '></div>' +
      '</div>' +
      '<div class="row"><div><label>Observações</label><textarea id="observacoes" rows="2"' + (jaRespondida ? ' disabled' : '') + '>' + esc(q.notes) + '</textarea></div></div>' +
      '<div class="row"><div><label>Anexar proposta (PDF/JPG/PNG, até 5 MB)</label><input type="file" id="proposta" accept="application/pdf,image/jpeg,image/png"' + (jaRespondida ? ' disabled' : '') + '></div></div>';
    if (!jaRespondida) {
      html += '<button id="enviar">Enviar cotação</button>';
    }
    html += '<p class="msg" id="mensagem"></p>';
    el('conteudo').innerHTML = html;
    el('conteudo').style.display = 'block';
    if (jaRespondida) { return; }
    el('enviar').addEventListener('click', function () { enviarCotacao(q); });
  }

  function enviarCotacao(q) {
    var itens = [];
    for (var i = 0; i < q.items.length; i++) {
      itens.push({
        quote_item_id: q.items[i].quote_item_id,
        unit_price: parseFloat(el('preco-' + i).value || '0'),
        lead_time_days: parseInt(el('prazo-' + i).value || '0', 10),
        declined: el('recusa-' + i).checked
      });
    }
    var corpo = {
      items: itens,
      freight_value: parseFloat(el('frete').value || '0'),
      payment_terms: el('pagamento').value,
      notes: el('observacoes').value
    };
    var arquivo = el('proposta').files[0];
    var botao = el('enviar');
    botao.disabled = true;
    function postar() {
      fetch(api + '/quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
      }).then(function (resposta) { return resposta.json().then(function (j) { return { ok: resposta.ok, json: j }; }); })
        .then(function (resultado) {
          var caixa = el('mensagem');
          if (resultado.ok) {
            caixa.className = 'msg ok';
            caixa.textContent = 'Cotação enviada com sucesso. Obrigado!';
            setTimeout(function () { window.location.reload(); }, 1500);
          } else {
            caixa.className = 'msg erro';
            caixa.textContent = (resultado.json && resultado.json.error && (resultado.json.error.message || resultado.json.error)) || 'Falha ao enviar.';
            botao.disabled = false;
          }
        })
        .catch(function () {
          el('mensagem').className = 'msg erro';
          el('mensagem').textContent = 'Falha de conexão. Tente novamente.';
          botao.disabled = false;
        });
    }
    if (arquivo) {
      if (arquivo.size > 5 * 1024 * 1024) {
        el('mensagem').className = 'msg erro';
        el('mensagem').textContent = 'A proposta excede 5 MB.';
        botao.disabled = false;
        return;
      }
      var leitor = new FileReader();
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
    el('subtitulo').textContent = dados.company_name + ' — Pedido ' + (po.po_number || ('#' + po.id)) + ' para ' + dados.supplier_name;
    var html = '<h2>Itens do pedido</h2>';
    html += '<table><thead><tr><th>Item</th><th class="esconde-mobile">CA</th><th>Qtde</th><th>Preço unit.</th></tr></thead><tbody>';
    po.items.forEach(function (item) {
      html += '<tr><td>' + esc(item.epi_name) + '</td><td class="esconde-mobile">' + esc(item.ca || '-') + '</td>' +
        '<td>' + item.quantity + '</td><td>' + moeda(item.unit_price) + '</td></tr>';
    });
    html += '</tbody></table>';
    if (po.supplier_confirmation_status) {
      html += '<p class="muted" style="margin-top:8px">Situação atual: <strong>' + esc(po.supplier_confirmation_status) + '</strong></p>';
    }
    html += '<h2>Registrar retorno</h2>' +
      '<div class="row">' +
      '<div><label>Ação</label><select id="acao">' +
      '<option value="confirmed">Confirmar pedido</option>' +
      '<option value="delivery_update">Atualizar entrega</option>' +
      '<option value="rejected">Recusar pedido</option>' +
      '</select></div>' +
      '<div><label>Previsão de entrega</label><input type="date" id="previsao" value="' + esc(po.expected_delivery_date) + '"></div>' +
      '</div>' +
      '<div class="row">' +
      '<div><label>Transportadora</label><input type="text" id="transportadora"></div>' +
      '<div><label>Código de rastreio</label><input type="text" id="rastreio"></div>' +
      '</div>' +
      '<div class="row"><div><label>Comentário</label><textarea id="comentario" rows="2"></textarea></div></div>' +
      '<button id="registrar">Registrar</button>' +
      '<p class="msg" id="mensagem"></p>';
    if (po.confirmations.length) {
      html += '<h2>Histórico</h2><table><thead><tr><th>Data</th><th>Ação</th><th class="esconde-mobile">Detalhes</th></tr></thead><tbody>';
      po.confirmations.forEach(function (c) {
        html += '<tr><td>' + esc(String(c.created_at).slice(0, 10)) + '</td><td>' + esc(c.status) + '</td>' +
          '<td class="esconde-mobile">' + esc([c.carrier, c.tracking_code, c.comment].filter(Boolean).join(' — ')) + '</td></tr>';
      });
      html += '</tbody></table>';
    }
    el('conteudo').innerHTML = html;
    el('conteudo').style.display = 'block';
    el('registrar').addEventListener('click', function () {
      var botao = el('registrar');
      botao.disabled = true;
      fetch(api + '/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: el('acao').value,
          delivery_forecast: el('previsao').value,
          carrier: el('transportadora').value,
          tracking_code: el('rastreio').value,
          comment: el('comentario').value
        })
      }).then(function (resposta) { return resposta.json().then(function (j) { return { ok: resposta.ok, json: j }; }); })
        .then(function (resultado) {
          var caixa = el('mensagem');
          if (resultado.ok) {
            caixa.className = 'msg ok';
            caixa.textContent = 'Registro enviado com sucesso. Obrigado!';
            setTimeout(function () { window.location.reload(); }, 1500);
          } else {
            caixa.className = 'msg erro';
            caixa.textContent = (resultado.json && resultado.json.error && (resultado.json.error.message || resultado.json.error)) || 'Falha ao registrar.';
            botao.disabled = false;
          }
        })
        .catch(function () {
          el('mensagem').className = 'msg erro';
          el('mensagem').textContent = 'Falha de conexão. Tente novamente.';
          botao.disabled = false;
        });
    });
  }

  fetch(api)
    .then(function (resposta) {
      if (!resposta.ok) { throw new Error('denied'); }
      return resposta.json();
    })
    .then(function (json) {
      dados = json.item;
      if (dados.entity_type === 'quote') { renderCotacao(dados.quote); }
      else { renderPedido(dados.purchase_order); }
    })
    .catch(function () {
      falha('Link inválido, expirado ou revogado. Solicite um novo link ao comprador.');
    });
})();
</script>
</body>
</html>
"""
