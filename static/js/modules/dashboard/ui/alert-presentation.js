'use strict';

// Presentation only: classification, scope, stock and expiry rules remain server-side.
(function () {
  const prefix = 'operationalAlerts.';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api = () => globalThis.EpiI18n;
  const measureKeys = {unidade:'unit', un:'unit', par:'pair'};
  const numberRef = value => ({type:'number',value});
  const messageRef = (key, vars, refs) => ({type:'message',key,vars,refs});

  function describe(item) {
    const metadata = item?.presentation;
    const fallback = {title:{text:String(item?.title || '')}, description:{text:String(item?.description || '')}, sizes:[]};
    if (!api() || !metadata || typeof metadata.title_key !== 'string' || typeof metadata.description_key !== 'string'
        || !metadata.title_key.startsWith(prefix) || !metadata.description_key.startsWith(prefix)) {return fallback;}
    const vars = {...metadata.params}, refs = {};
    for (const field of ['stock','minimum','count','days']) {
      if (Number.isFinite(Number(vars[field])) && vars[field] !== undefined) {refs[field] = numberRef(vars[field]);}
    }
    if (vars.date) {refs.date = {type:'date',value:vars.date};}
    const measure = measureKeys[vars.measure];
    if (measure) {refs.measure = messageRef(prefix + 'measure.' + measure, {count:Number(vars.stock)});}
    if (vars.days !== undefined) {refs.daysLabel = messageRef(prefix + 'days', {count:Number(vars.days)}, {count:numberRef(vars.days)});}
    const titleText = api().t(metadata.title_key, vars);
    const descriptionText = api().t(metadata.description_key, vars);
    // A newer backend may send a key unknown to this frontend. Keep its complete legacy message.
    if (titleText === metadata.title_key || descriptionText === metadata.description_key) {return fallback;}
    const descriptor = key => ({key,vars,refs,text:api().t(key,vars)});
    const result = {title:descriptor(metadata.title_key), description:descriptor(metadata.description_key), sizes:[]};
    if (item.category === 'stock') {
      for (const balance of item.size_balances || []) {
        const labels=[];
        for (const [field,label] of [['glove_size','glove'],['size','size'],['uniform_size','uniform']]) {
          if (balance[field] && balance[field] !== 'N/A') {labels.push({key:prefix+'size.'+label,vars:{value:balance[field]}});}
        }
        result.sizes.push({labels,quantity:balance.quantity ?? 0});
      }
    }
    return result;
  }

  function text(message) {
    if (!message.key) {return message.text;}
    // Resolve typed date/number/message variables through the same engine as live DOM bindings.
    const node = globalThis.document.createElement('span');
    node.textContent = api().textFor(node,message.key,message.text,message.vars,message.refs);
    return node.textContent;
  }

  function markup(message) {
    return message.key ? api().bindText(message.key,message.vars,message.text,message.refs) : escape(message.text);
  }

  function sizeMarkup(sizes) {
    if (!sizes.length) {return '';}
    const entries = sizes.map(size => {
      const labels = size.labels.length ? size.labels.map(label => markup(label)).join(' ')
        : api().bindText(prefix+'size.unspecified',{},'S/Tam');
      return labels + '×' + api().bindText(prefix+'quantity',{count:size.quantity},String(size.quantity),{count:numberRef(size.quantity)});
    });
    return ' | ' + api().bindText(prefix+'sizes',{},'Tamanhos em estoque:') + ' ' + entries.join(', ');
  }

  function sizeText(sizes) {
    return sizes.map(size => (size.labels.length ? size.labels.map(label => api().t(label.key,label.vars)).join(' ')
      : api().t(prefix+'size.unspecified')) + '×' + api().formatNumber(size.quantity)).join(', ');
  }

  globalThis.__EPI_ALERT_PRESENTATION__ = Object.freeze({describe,text,markup,sizeMarkup,sizeText});
})();
