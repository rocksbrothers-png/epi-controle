'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
function functionSource(name) {
  const start = new RegExp('^(?:async )?function ' + name + '\\(', 'm').exec(source);
  if (!start) throw new Error('Função ausente: ' + name);
  const end = source.slice(start.index + start[0].length).search(/^}/m);
  return source.slice(start.index, start.index + start[0].length + end + 1);
}

function harness() {
  const nodes = new Map(), sent = [], toasts = [], modalCalls = [];
  let selected = [], allowed = true;
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, { id, value: '', innerHTML: '', textContent: '', style: {},
      listeners: {}, dataset: {}, remove() {},
      querySelectorAll: () => [{checked:true,dataset:{index:'0'}}],
      querySelector: (selector) => selector.startsWith('.reg-piece-size') ? node('reg-test-size') : node(selector.slice(1)) });
    return nodes.get(id);
  };
  node('reg-test-size').value = 'M';
  const context = {
    console, URLSearchParams, Map, Array,
    crypto: { randomUUID: () => '12345678901234567890123456789012' },
    document: { getElementById: node, querySelectorAll: (selector) => selector.includes('group-select') ? [] : selected,
      createElement: () => node('overlay'), body: { appendChild() {} } },
    state: { user: { id: 1 } },
    bindAppListener: (target, event, callback) => { target.listeners[event] = callback; },
    esc: (s) => String(s ?? ''), tr: (_key, fallback) => fallback,
    FileReader: class { readAsDataURL(file) { this.result = 'data:image/png;base64,RE9DVU1FTlRP'; if (file.fail) this.onerror(); else this.onload(); } },
    hasPermission: () => allowed, showToast: (...args) => toasts.push(args),
    _blockedStockContext: () => ({ companyId: '2', unitId: '5' }),
    _stockPanelRequests: new Map(),
    api: async (url, options) => { sent.push({ url, body: JSON.parse(options.body) }); return { items: [] }; },
    apiWithBootstrapRetry: async () => ({ items: [] }),
    loadPendingRegularization: async () => {}, loadValidityOverview: async () => {}, loadBlockedStock: async () => {}
  };
  vm.createContext(context);
  const names = ['readStockEvidenceFile', 'openRegularizeValidityModal', 'regularizePendingPiece',
    'regularizeSelectedStockLot', 'pendingRegularizationProof', 'reviewPendingRegularizationLots', 'updatePendingRegularizationSelection', 'groupPendingRegularizationItems', 'pendingRegularizationGroupLabel', 'applyPendingRegularizationFilter', 'selectPendingRegularizationRows', 'reconcileStockLot', 'loadStockLotEvidence', '_startStockPanelLoad', '_stockPanelLoadMessage', '_stockPanelLoadError'];
  vm.runInContext(names.map(functionSource).join('\n'), context);
  return {
    node, sent, toasts, modalCalls, context,
    run: (code) => vm.runInContext(code, context),
    allowed: (value) => { allowed = value; },
    selected: (rows) => { selected = rows.map((dataset) => ({ dataset })); },
    captureModal: () => { context.openRegularizeValidityModal = async (piece) => { modalCalls.push(piece); return null; }; }
  };
}

const file = { name: 'etiqueta.png', type: 'image/png', size: 68 };
module.exports = ({ testAsync, assert, eq }) => {
  testAsync('Lote físico: seleção exige mesmo EPI/unidade e transmite todos os QRs explícitos', async () => {
    const h = harness(); h.captureModal();
    const a = { id: '1', qr: 'QR-1', epi: '10', unit: '5', name: 'Luva', lot: '' };
    h.selected([a, { ...a, id: '2', qr: 'QR-2', epi: '11' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0); eq(h.toasts.length, 1);
    h.selected([a, { ...a, id: '2', qr: 'QR-2' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 1);
    eq(h.modalCalls[0].items.length, 2);
    eq(h.modalCalls[0].items[1].qr_code, 'QR-2');
  });

  testAsync('Lote físico: sem seleção ou sem permissão não abre conferência', async () => {
    const h = harness(); h.captureModal();
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0); eq(h.toasts.length, 1);
    h.allowed(false); h.selected([{ id: '1', qr: 'QR-1', epi: '10', unit: '5' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0);
  });

  testAsync('Lote físico: modal exige lote, anexo e conferência física antes de confirmar', async () => {
    const h = harness();
    const promise = h.run("openRegularizeValidityModal({ id: 1, qr: 'QR-1', epiName: 'Luva' })");
    h.node('reg-date').value = '2027-01-01';
    h.node('reg-manufacture').value = '2025-01-21';
    h.node('reg-evidence').value = 'Etiqueta';
    h.node('reg-justification').value = 'Conferência';
    h.node('reg-source').value = 'label';
    const confirm = h.node('reg-confirm').listeners.click;
    await confirm(); assert(h.node('reg-error').textContent.includes('lote real'));
    h.node('reg-lot').value = 'A';
    await confirm(); assert(h.node('reg-error').textContent.includes('conferência física'));
    h.node('reg-physical-confirm').checked = true;
    await confirm(); assert(h.node('reg-error').textContent.includes('Anexe foto'));
    h.node('reg-file').files = [file];
    await confirm();
    const result = await promise;
    eq(result.lot, 'A'); eq(result.file.filename, 'etiqueta.png');
    eq(result.source, 'label'); eq(result.manufacture, '2025-01-21');
  });

  testAsync('Lote físico: leitura do arquivo rejeita formato, tamanho e falha de leitura', async () => {
    const h = harness();
    for (const candidate of [{ ...file, type: 'text/html' }, { ...file, size: 4 * 1024 * 1024 }, { ...file, fail: true }]) {
      h.node('input').files = [candidate];
      let failed = false;
      try { await h.run("readStockEvidenceFile(document.getElementById('input'))"); } catch { failed = true; }
      assert(failed);
    }
  });

  testAsync('Lote físico: regularização envia lote, prova e seleção ao endpoint próprio', async () => {
    const h = harness();
    h.context.openRegularizeValidityModal = async () => ({ date: '2027-01-01', evidence: 'Etiqueta A',
      justification: 'Conferência', lot: 'A', source: 'label', file: { filename: 'etiqueta.png' } });
    await h.run("regularizePendingPiece({ id: 1, qr: 'QR-1', unitId: 5, items: [{ stock_item_id: 1, qr_code: 'QR-1' }, { stock_item_id: 2, qr_code: 'QR-2' }] })");
    eq(h.sent.length, 1);
    assert(h.sent[0].url.includes('/lots/'));
    eq(h.sent[0].body.items.length, 2);
    eq(h.sent[0].body.lot_code, 'A'); eq(h.sent[0].body.physical_lot_confirmed, true);
    eq(h.sent[0].body.evidence_file.filename, 'etiqueta.png');
  });

  testAsync('Lote físico: consulta distingue erro de lote vazio e renderiza download autenticado', async () => {
    const h = harness();
    h.context.apiWithBootstrapRetry = async () => { throw new Error('503'); };
    await h.run('loadStockLotEvidence()');
    assert(h.node('stock-lot-status').textContent.includes('Não foi possível carregar'));
    eq(h.node('stock-lot-empty').style.display, 'none');
    h.context.apiWithBootstrapRetry = async () => ({ items: [{ id: 8, lot_code: 'A', has_file: true }] });
    await h.run('loadStockLotEvidence()');
    assert(h.node('stock-lot-tbody').innerHTML.includes('data-lot-evidence="8"'));
  });

  testAsync('Lote físico: conciliação envia contagem explícita e apresenta os QRs gerados', async () => {
    const h = harness();
    h.node('stock-epi').value = '10';
    h.context.openRegularizeValidityModal = async (piece) => {
      assert(piece.reconcile);
      return { date: '2027-01-01', evidence: 'Etiqueta', justification: 'Contagem',
        lot: 'A', source: 'label', file: {}, quantity: 2, size: 'M', manufacture: '' };
    };
    const requests = [], printed = [];
    h.context.api = async (url, options) => { requests.push({ url, body: JSON.parse(options.body) }); return { qr_labels: [{ qr_code_value: 'NOVO-QR' }] }; };
    h.context.printStockLabels = (labels) => printed.push(labels);
    h.context.__EPI_REFRESH_ESTOQUE_LISTA__ = async () => {};
    await h.run('reconcileStockLot()');
    eq(requests.length, 1);
    assert(requests[0].url.endsWith('/reconcile'));
    eq(requests[0].body.quantity, 2); eq(requests[0].body.epi_id, 10);
    eq(requests[0].body.physical_lot_confirmed, true);
    assert(requests[0].body.idempotency_key);
    eq(printed.length, 1); eq(printed[0][0].qr_code_value, 'NOVO-QR');
    eq(h.node('stock-lot-reconcile').disabled, false);
  });

  testAsync('Lote físico: cancelar conciliação não envia dados e restaura o botão', async () => {
    const h = harness();
    h.node('stock-epi').value = '10'; h.captureModal();
    await h.run('reconcileStockLot()');
    eq(h.sent.length, 0); eq(h.node('stock-lot-reconcile').disabled, false);
  });
  testAsync('Lotes: agrupamento preserva lote real, recebimento e peças sem identidade', async () => {
    const h = harness();
    const rows = h.run(`groupPendingRegularizationItems([
      {id:1,epi_id:10,unit_id:5,lot_id:7,stock_movement_id:1},
      {id:2,epi_id:10,unit_id:5,lot_id:7,stock_movement_id:2},
      {id:3,epi_id:10,unit_id:5,stock_movement_id:3,lot_code:'A'},
      {id:4,epi_id:10,unit_id:5,stock_movement_id:4,lot_code:'A'},
      {id:5,epi_id:10,unit_id:5},{id:6,epi_id:10,unit_id:5},
      {id:7,epi_id:11,unit_id:5,lot_id:7}])`);
    eq(rows.length, 5); eq(rows[0].items.length, 2); eq(rows[3].items.length, 2); assert(rows[3].unidentified);
  });

  const selections = [
    { id:'1', qr:'QR-1', epi:'10', unit:'5', group:'A', name:'Luva', lot:'A' },
    { id:'2', qr:'QR-2', epi:'11', unit:'5', group:'B', name:'Capacete', lot:'B' }
  ];
  const proof = (piece) => ({ lot:piece.lot, date:piece.lot === 'A' ? '2027-01-01' : '2028-02-02',
    evidence:'Etiqueta ' + piece.lot, justification:'Conferência ' + piece.lot, source:'label',
    file:{filename:piece.lot + '.png', content_base64:'QUJD'} });

  testAsync('Lotes: um único envio preserva datas, arquivos, justificativas e QRs separados', async () => {
    const h=harness(); h.selected(selections);
    h.context.openRegularizeValidityModal = async (piece) => {
      eq(h.sent.length,0); eq(piece.queueTotal,2); return proof(piece);
    };
    h.context.reviewPendingRegularizationLots = async (lots) => { eq(h.sent.length,0); eq(lots.length,2); return true; };
    await h.run('regularizeSelectedStockLot()');
    eq(h.sent.length,1); const lots=h.sent[0].body.lots;
    eq(lots.length,2); eq(lots[0].physical_expiry_date,'2027-01-01'); eq(lots[1].physical_expiry_date,'2028-02-02');
    eq(lots[0].evidence_file.filename,'A.png'); eq(lots[1].evidence_file.filename,'B.png');
    eq(lots[0].items[0].qr_code,'QR-1'); eq(lots[1].justification,'Conferência B');
    eq(h.context.regularizeSelectedStockLot.busy,false);
  });

  for (const cancel of ['proof','review']) testAsync('Lotes: cancelar ' + cancel + ' não envia nenhum lote', async () => {
    const h=harness(); h.selected(selections);
    h.context.openRegularizeValidityModal = async (piece) => cancel === 'proof' && piece.queueIndex === 2 ? null : proof(piece);
    h.context.reviewPendingRegularizationLots = async () => false;
    await h.run('regularizeSelectedStockLot()'); eq(h.sent.length,0);
    eq(h.context.regularizeSelectedStockLot.busy,false);
  });

  testAsync('Lotes: clique no grupo regulariza o grupo inteiro mesmo sem checkboxes marcadas', async () => {
    const h=harness(); h.captureModal();
    h.context.groupNodes=selections.slice(0,1).map((dataset)=>({dataset}));
    await h.run('regularizeSelectedStockLot(groupNodes)');
    eq(h.modalCalls.length,1); eq(h.modalCalls[0].items[0].stock_item_id,1);
  });

  testAsync('Lotes: selecionar exibidos preserva seleção oculta; limpar remove ambas', async () => {
    const h=harness();
    const rows=selections.map((dataset,i)=>({dataset,checked:false,closest:()=>({hidden:i===1})}));
    h.context.document.querySelectorAll=(selector)=>selector.includes('group-select') ? [] : rows;
    await h.run('selectPendingRegularizationRows(true)'); eq(rows[0].checked,true); eq(rows[1].checked,false);
    rows[1].checked=true;
    await h.run('selectPendingRegularizationRows(false)'); assert(rows.every((row)=>!row.checked));
  });

  testAsync('Lotes: seleção parcial marca cabeçalho indeterminado e conta grupos', async () => {
    const h=harness(); const rows=selections.map((dataset,i)=>({dataset:{...dataset,group:'A'},checked:i===0}));
    const header={dataset:{group:'A'}};
    h.context.document.querySelectorAll=(selector)=>selector.includes('group-select') ? [header] : rows;
    await h.run('updatePendingRegularizationSelection()'); eq(header.indeterminate,true); eq(header.checked,false);
    assert(h.node('pending-reg-selection-count').textContent.includes('1 peça(s) em 1'));
    rows[1].checked=true; await h.run('updatePendingRegularizationSelection()'); eq(header.indeterminate,false); eq(header.checked,true);
  });

  testAsync('Lotes: mudança de escopo e erro no envio restauram seleção sem falso sucesso', async () => {
    for(const changeScope of [true,false]) {
      const h=harness(); h.selected(selections);
      h.context.openRegularizeValidityModal=async(piece)=>proof(piece);
      h.context.reviewPendingRegularizationLots=async()=>{
        if(changeScope) h.context._blockedStockContext=()=>({companyId:'3',unitId:'6'});
        return true;
      };
      h.context.api=async()=>{throw new Error('Envio recusado');};
      await h.run('regularizeSelectedStockLot()');
      eq(h.toasts.length,1); eq(h.toasts[0][1],'error'); eq(h.context.regularizeSelectedStockLot.busy,false);
    }
  });

  testAsync('Lotes: duplo clique durante conferência não abre outro fluxo', async () => {
    const h=harness(); h.selected(selections); let release, calls=0;
    h.context.openRegularizeValidityModal=()=>{calls++;return new Promise((resolve)=>{release=resolve;});};
    const pending=h.run('regularizeSelectedStockLot()');
    await h.run('regularizeSelectedStockLot()'); eq(calls,1); release(null); await pending;
    eq(h.sent.length,0);
  });

  testAsync('Lotes: revisão final mostra dados de cada lote e exige confirmação própria', async () => {
    const h=harness();
    h.context.reviewLots=selections.map((row)=>({piece:{epiName:row.name,items:[{qr_code:row.qr}]},proof:proof(row)}));
    const pending=h.run('reviewPendingRegularizationLots(reviewLots)');
    const html=h.node('overlay').innerHTML;
    assert(html.includes('2027-01-01')); assert(html.includes('2028-02-02'));
    assert(html.includes('A.png')); assert(html.includes('B.png'));
    assert(html.includes('Conferência B')); assert(html.includes('2 lotes / 2 peças'));
    h.node('reg-review-confirm').listeners.click(); eq(await pending,true);
    const cancelled=h.run('reviewPendingRegularizationLots(reviewLots)');
    h.node('reg-review-cancel').listeners.click(); eq(await cancelled,false);
  });

  testAsync('Lotes: limites de peças/grupos e unidade diferente impedem os formulários', async () => {
    for(const rows of [Array.from({length:501},(_,i)=>({...selections[0],id:String(i)})),
        Array.from({length:11},(_,i)=>({...selections[0],group:String(i),id:String(i)})),
        [selections[0],{...selections[1],unit:'6'}]]) {
      const h=harness(); h.captureModal(); h.selected(rows);
      await h.run('regularizeSelectedStockLot()'); eq(h.modalCalls.length,0); eq(h.toasts.length,1);
    }
  });

  testAsync('Lotes: separar QRs de um recebimento prepara duas provas em um único envio', async () => {
    const h=harness(); h.selected([selections[0],{...selections[0],id:'2',qr:'QR-2'}]);
    let count=0;
    h.context.openRegularizeValidityModal=async(piece)=>{
      count++; eq(h.sent.length,0);
      return {...proof({...piece,lot:count===1?'A':'B'}),items:[piece.items[0]]};
    };
    h.context.reviewPendingRegularizationLots=async(lots)=>{eq(lots.length,2);return true;};
    await h.run('regularizeSelectedStockLot()');
    eq(h.sent.length,1); const lots=h.sent[0].body.lots;
    eq(lots[0].items.length,1); eq(lots[0].items[0].qr_code,'QR-1');
    eq(lots[1].items.length,1); eq(lots[1].items[0].qr_code,'QR-2');
    eq(lots[0].lot_code,'A'); eq(lots[1].lot_code,'B');
  });

  testAsync('Lotes: filtro oculta grupos sem apagar sua seleção', async () => {
    const h=harness(); const rows=selections.map((row)=>({dataset:{pendingGroup:row.group},hidden:false}));
    const checks=selections.map((dataset)=>({dataset,checked:true}));
    h.context.document.querySelectorAll=(selector)=>selector.includes('tr[') ? rows : selector.includes('group-select') ? [] : checks;
    h.node('pending-reg-filter').value='A'; await h.run('applyPendingRegularizationFilter()');
    eq(rows[0].hidden,false); eq(rows[1].hidden,true); assert(checks.every((node)=>node.checked));
    assert(h.node('pending-reg-selection-count').textContent.includes('2 peça(s) em 2'));
    h.node('pending-reg-filter').value=''; await h.run('applyPendingRegularizationFilter()');
    assert(rows.every((row)=>!row.hidden));
  });

  testAsync('Lotes: formulário permite separar QRs e exige ao menos uma peça na comprovação', async () => {
    const h=harness();
    const checks=[{checked:false,dataset:{index:'0'}},{checked:false,dataset:{index:'1'}}];
    h.node('overlay').querySelectorAll=()=>checks;
    const pending=h.run("openRegularizeValidityModal({epiName:'Luva',items:[{stock_item_id:1,qr_code:'Q1'},{stock_item_id:2,qr_code:'Q2'}]})");
    const confirm=h.node('reg-confirm').listeners.click;
    await confirm(); assert(h.node('reg-error').textContent.includes('ao menos uma'));
    checks[1].checked=true;
    for (const [id,value] of [['reg-lot','L2'],['reg-date','2028-01-01'],['reg-evidence','Etiqueta L2'],['reg-justification','Conferência'],['reg-source','label']]) h.node(id).value=value;
    h.node('reg-physical-confirm').checked=true; h.node('reg-file').files=[file];
    await confirm(); const result=await pending;
    eq(result.items.length,1); eq(result.items[0].stock_item_id,2); eq(result.items[0].qr_code,'Q2');
  });

};
