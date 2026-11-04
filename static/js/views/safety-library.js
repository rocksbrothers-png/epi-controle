/* Private library: credentials stay in closures; only authorized PNG pages are displayed. */
(() => {
  'use strict';
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const tr = (key, fallback, vars) => globalThis.trEpi?.(key, fallback, vars)
    ?? String(fallback).replace(/\{(\w+)\}/g, (match, name) => Object.prototype.hasOwnProperty.call(vars || {}, name) ? String(vars[name]) : match);
  const categories = {
    get epi_matrix() { return tr('safetyLibrary.category.epi_matrix', 'Matriz de Aplicação de EPIs'); },
    get glove_matrix() { return tr('safetyLibrary.category.glove_matrix', 'Matriz de Seleção de Luvas'); },
    get care_guides() { return tr('safetyLibrary.category.care_guides', 'Guias de Higienização e Conservação'); },
    get use_instructions() { return tr('safetyLibrary.category.use_instructions', 'Instruções de Uso dos EPIs'); },
    get technical_manuals() { return tr('safetyLibrary.category.technical_manuals', 'Manuais e Fichas Técnicas'); },
    get other_sst() { return tr('safetyLibrary.category.other_sst', 'Outros Documentos de SST'); }
  };
  const option = (id, label, key) => `<option value="${esc(id)}"${key ? ` data-i18n="${esc(key)}"` : ''}>${esc(label)}</option>`;
  function client({token, cpfLast3} = {}) {
    const admin = !token;
    return async (action, data = {}, bytes = false) => {
      const path = `/api/${admin ? 'safety' : 'employee'}-library/${action}`;
      const options = {method:'POST', body:JSON.stringify(admin ? data : {...data, token, cpf_last3:cpfLast3}), cache:'no-store'};
      const response = admin
        ? await globalThis.requestApiResponse(path, options)
        : await fetch(path, {...options, credentials:'same-origin', headers:{'Content-Type':'application/json'}});
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const localized = globalThis.EpiI18n?.describeApiError?.(error, typeof error.error === 'string' ? error.error : (globalThis.trEpi?.('ui.safety_library.acesso_a_biblioteca_recusado_3dc3e3','Acesso \u00e0 biblioteca recusado.',{}) ?? 'Acesso \u00e0 biblioteca recusado.')) || {text:typeof error.error === 'string' ? error.error : (globalThis.trEpi?.('ui.safety_library.acesso_a_biblioteca_recusado_3dc3e3','Acesso \u00e0 biblioteca recusado.',{}) ?? 'Acesso \u00e0 biblioteca recusado.')};
        throw Object.assign(new Error(localized.text), {i18n:localized, status:response.status, code:error.code || error.error?.code || error.validation?.code || '', payload:error});
      }
      return bytes ? response.blob() : response.json();
    };
  }
  function status(root, message, error = false, binding) {
    const node = root.querySelector('[data-library-status]');
    if (message && typeof message === 'object') {binding = binding || message.i18n; message = message.message || String(message);}
    if (node && !binding?.key) {globalThis.EpiI18n?.clearBinding?.(node);}
    if (node) { node.textContent = binding?.key ? (globalThis.EpiI18n?.textFor?.(node, binding.key, message, binding.vars, binding.refs) ?? message) : message; node.setAttribute('role',error ? 'alert':'status'); }
  }
  function dialog(title, key) {
    const node = document.createElement('dialog');
    node.className = 'safety-dialog';
    node.innerHTML = `<header><h2${key ? ` data-i18n="${esc(key)}"` : ''}>${esc(title)}</h2><button type="button" data-close aria-label="Fechar" data-i18n-aria-label="close" data-i18n="close">Fechar</button></header><div data-content></div>`;
    document.body.append(node);
    node.querySelector('[data-close]').onclick = () => node.close();
    node.addEventListener('close', () => node.remove());
    node.showModal();
    return node;
  }
  async function viewer(request, document) {
    const modal = dialog(document.title);
    const content = modal.querySelector('[data-content]');
    content.innerHTML = '<p role="status" data-i18n="ui.safety_library.carregando_pre_visualizacao_f01fea">Carregando pr\u00e9-visualiza\u00e7\u00e3o\u2026</p>';
    let url;
    let sequence = 0;
    modal.addEventListener('close', () => { sequence++; if(url) {URL.revokeObjectURL(url);} });
    try {
      const result = await request('manifest',{document_id:document.document_id,version_id:document.id});
      if (!modal.isConnected) {return;}
      const parts = result.preview.parts;
      let part = 0, page = 0, scale = 1;
      content.innerHTML = `<p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.versao_p0_vigencia_p1_e02009',{p0:(document.version_label),p1:(document.effective_date)},'Vers\u00e3o {p0} \u00b7 Vig\u00eancia {p1}',{p1:{type:'date',value:document.effective_date}}) ?? `Versão ${esc(document.version_label)} · Vigência ${esc(document.effective_date)}`)}</p>
        ${(result.preview.warnings || []).map(w => {const message=globalThis.EpiI18n?.describeApiError?.(w,w);return `<p role="note">${message?.key ? (globalThis.EpiI18n?.bindText?.(message.key,message.vars,message.text,message.refs) ?? esc(message.text)) : esc(w)}</p>`;}).join('')}
        <div class="safety-viewer-tools"><label data-i18n="ui.safety_library.aba_770e56">Aba <select data-part>${parts.map(p=>{const key=p.name_i18n_key || (result.preview.renderer==='safe-raster-v1' ? 'safetyLibrary.preview.image' : result.preview.renderer==='pymupdf-raster-v1' ? 'safetyLibrary.preview.document' : '');return option(p.index,key?tr(key,p.name):p.name,key);}).join('')}</select></label>
        <button data-prev data-i18n="previous">Anterior</button><span data-counter></span><button data-next data-i18n="ui.safety_library.proxima_2fe966">Próxima</button>
        <button data-less aria-label="Diminuir zoom" data-i18n-aria-label="ui.safety_library.diminuir_zoom_c8bed7">−</button><span data-zoom>100%</span><button data-more aria-label="Aumentar zoom" data-i18n-aria-label="ui.safety_library.aumentar_zoom_68eea7">+</button><button data-fit data-i18n="ui.safety_library.ajustar_7c7b26">Ajustar</button></div>
        <p data-library-status role="status"></p><div class="safety-page-viewport"><img data-page draggable="false" alt="Pré-visualização do documento" data-i18n-alt="ui.safety_library.pre_visualizacao_do_documento_309923"></div>`;
      const image = content.querySelector('[data-page]');
      image.oncontextmenu = event => event.preventDefault();
      const zoom = () => {image.style.width = `${scale * 100}%`; content.querySelector('[data-zoom]').textContent=`${Math.round(scale*100)}%`;};
      const load = async () => {
        const current = ++sequence;
        status(content,(globalThis.trEpi?.('ui.safety_library.carregando_pagina_10906d','Carregando p\u00e1gina\u2026',{}) ?? 'Carregando p\u00e1gina\u2026'),false,{key:'ui.safety_library.carregando_pagina_10906d',vars:{}}); image.hidden = true;
        content.querySelector('[data-counter]').textContent = `${page+1} / ${parts[part].pages.length}`;
        content.querySelector('[data-prev]').disabled = page===0;
        content.querySelector('[data-next]').disabled = page===parts[part].pages.length-1;
        try {
          const blob = await request('page',{document_id:document.document_id,version_id:document.id,part_index:part,page_index:page},true);
          if(current!==sequence || !modal.isConnected) {return;}
          if(url) {URL.revokeObjectURL(url);}
          url=URL.createObjectURL(blob);image.src=url;image.hidden=false;zoom();status(content,'');
        } catch(e) { if(current===sequence) {status(content,e,true);} }
      };
      content.querySelector('[data-part]').onchange=e=>{part=Number(e.target.value);page=0;scale=1;void load();};
      content.querySelector('[data-prev]').onclick=()=>{page--;void load();};
      content.querySelector('[data-next]').onclick=()=>{page++;void load();};
      content.querySelector('[data-less]').onclick=()=>{scale=Math.max(.5,scale-.25);zoom();};
      content.querySelector('[data-more]').onclick=()=>{scale=Math.min(4,scale+.25);zoom();};
      content.querySelector('[data-fit]').onclick=()=>{scale=1;zoom();};
      await load();
    } catch(e) {content.textContent=((globalThis.EpiI18n?.textFor?.(content,'ui.safety_library.pre_visualizacao_indisponivel_p0_c4783f','Pr\u00e9-visualiza\u00e7\u00e3o indispon\u00edvel: {p0}',{p0:(e.message)},e.i18n?.key ? {p0:{type:'message',key:e.i18n.key,vars:e.i18n.vars,refs:e.i18n.refs}} : {}) ?? globalThis.trEpi?.('ui.safety_library.pre_visualizacao_indisponivel_p0_c4783f','Pr\u00e9-visualiza\u00e7\u00e3o indispon\u00edvel: {p0}',{p0:(e.message)})) ?? `Pré-visualização indisponível: ${e.message}`);}
  }
  const epiFields = [
    [
        'name',
        'dashboard.tableEpi',
        'EPI'
    ],
    [
        'manufacturer',
        'dashboard.tableManufacturer',
        'Fabricante'
    ],
    [
        'model_reference',
        'dashboard.tableModelReference',
        'Modelo/referência'
    ],
    [
        'ca',
        'epi.caShort',
        'CA'
    ],
    [
        'ca_expiry',
        'dashboard.tableCaExpiry',
        'Validade do CA'
    ],
    [
        'manufacturer_validity_months',
        'dashboard.tableUsefulLifeMonths',
        'Vida útil (meses)'
    ],
    [
        'sector',
        'dashboard.tableProtection',
        'Proteção'
    ],
    [
        'epi_section',
        'dashboard.tableSection',
        'Seção'
    ],
    [
        'manufacturer_recommendations',
        'dashboard.tableRecommendationRestriction',
        'Recomendações/restrições'
    ]
];
  function catalogueMarkup(items) {
    const missingKey = key => key === 'manufacturer_validity_months' ? 'safetyLibrary.notProvidedFeminine' : 'safetyLibrary.notProvided';
    const value = (item,key) => {
      if (!item[key]) {return globalThis.EpiI18n?.bindText?.(missingKey(key), {}, 'Não informado') ?? esc(tr(missingKey(key), 'Não informado'));}
      if (key === 'ca_expiry') {return globalThis.EpiI18n?.bindText?.('safetyLibrary.value',{value:item[key]},'{value}',{value:{type:'date',value:item[key]}}) ?? esc(item[key]);}
      return esc(item[key]);
    };
    return `<div class="safety-desktop"><table><thead><tr>${epiFields.map(([,key,label])=>`<th data-i18n="${key}">${esc(tr(key,label))}</th>`).join('')}<th data-i18n="dashboard.tablePhoto">Foto</th><th data-i18n="tabs.details">Detalhes</th></tr></thead><tbody>
      ${items.map(e=>`<tr>${epiFields.map(([key])=>`<td>${value(e,key)}</td>`).join('')}<td>${e.has_photo?`<span data-catalogue-photo="${e.id}"></span>`:'<span data-i18n="ui.safety_library.sem_foto_b1462b">Sem foto</span>'}</td><td><button data-epi="${e.id}" data-i18n="ui.safety_library.ver_epi_b914b6">Ver EPI</button></td></tr>`).join('')}</tbody></table></div>
      <div class="safety-mobile">${items.map(e=>`<article class="safety-card"><h3>${esc(e.name)}</h3>${e.has_photo?`<span data-catalogue-photo="${e.id}"></span>`:''}<p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.p2_ca_p3_1454f3',{p2:(e.manufacturer),p3:(e.ca)},'{p2} \u00b7 CA {p3}') ?? `${esc(e.manufacturer)} · CA ${esc(e.ca)}`)}</p><p>${esc(e.sector)}</p><button data-epi="${e.id}" data-i18n="ui.safety_library.ver_epi_e_documentos_8917c5">Ver EPI e documentos</button></article>`).join('')}</div>`;
  }
  async function portal(approvedRoot, libraryRoot, credentials) {
    const request = client(credentials);
    approvedRoot.innerHTML='<p role="status" data-i18n="ui.safety_library.carregando_catalogo_aprovado_010781">Carregando cat\u00e1logo aprovado\u2026</p>';
    libraryRoot.innerHTML='<p role="status" data-i18n="ui.safety_library.carregando_biblioteca_3374af">Carregando biblioteca\u2026</p>';
    try {
      const [episResult, docsResult] = await Promise.all([request('approved-epis'),request('documents')]);
      const epis = episResult.items, documents = docsResult.items;
      const photos = new Map();
      const photoUrls = [];
      globalThis.addEventListener('pagehide', () => photoUrls.forEach(url=>URL.revokeObjectURL(url)), {once:true});
      approvedRoot.innerHTML=`<h3 data-i18n="ui.safety_library.epis_aprovados_310d69">EPIs Aprovados</h3><p data-i18n="ui.safety_library.aprovacao_cadastral_da_empresa_a_validade_do_ca_nao_e_a_validade_fisica_de__5b4af7">Aprovação cadastral da empresa. A validade do CA não é a validade física de um lote; este catálogo não informa disponibilidade para entrega.</p>
        <div class="safety-filters">${[['name', 'dashboard.approvedSearchName', 'Buscar por Nome do EPI'], ['sector', 'dashboard.approvedSearchProtection', 'Buscar por Proteção'], ['ca', 'dashboard.approvedSearchCa', 'Buscar pelo CA brasileiro'], ['manufacturer', 'dashboard.approvedSearchManufacturer', 'Buscar por Fabricante'], ['epi_section', 'dashboard.approvedSearchSection', 'Buscar por Seção']].map(([key,labelKey,fallback])=>`<input type="search" data-epi-filter="${key}" data-i18n-aria-label="${labelKey}" data-i18n-placeholder="${labelKey}" aria-label="${esc(tr(labelKey,fallback))}" placeholder="${esc(tr(labelKey,fallback))}">`).join('')}</div><div data-epis></div>`;
      const paint = () => {
        const filtered = epis.filter(e=>[...approvedRoot.querySelectorAll('[data-epi-filter]')].every(f=>String(e[f.dataset.epiFilter]||'').toLocaleLowerCase().includes(f.value.trim().toLocaleLowerCase())));
        const target=approvedRoot.querySelector('[data-epis]'); target.innerHTML=filtered.length ? catalogueMarkup(filtered) : '<p data-i18n="ui.safety_library.nenhum_epi_aprovado_neste_contexto_f30749">Nenhum EPI aprovado neste contexto.</p>';
        target.querySelectorAll('[data-catalogue-photo]').forEach(async node=>{
          const id=Number(node.dataset.cataloguePhoto);
          try{
            if(!photos.has(id)){photos.set(id,request('photo',{epi_id:id},true).then(blob=>{const url=URL.createObjectURL(blob);photoUrls.push(url);return url;}));}
            const url=await photos.get(id);if(!node.isConnected){return;}
            const image=document.createElement('img');image.src=url;image.setAttribute('data-i18n-alt','ui.safety_library.foto_do_epi_7e4eb9');image.alt=((globalThis.EpiI18n?.attributeFor?.(image,'alt','ui.safety_library.foto_do_epi_7e4eb9','Foto do EPI',{}) ?? globalThis.trEpi?.('ui.safety_library.foto_do_epi_7e4eb9','Foto do EPI',{}) ?? 'Foto do EPI'));image.style.width='64px';image.style.height='64px';image.style.objectFit='contain';image.oncontextmenu=event=>event.preventDefault();node.append(image);
          }catch{node.textContent=((globalThis.EpiI18n?.textFor?.(node,'ui.safety_library.foto_indisponivel_ace218','Foto indispon\u00edvel',{}) ?? globalThis.trEpi?.('ui.safety_library.foto_indisponivel_ace218','Foto indispon\u00edvel',{})) ?? 'Foto indispon\u00edvel');}
        });
        target.querySelectorAll('[data-epi]').forEach(button=>{button.onclick=async()=>{
          const epi=epis.find(e=>e.id===Number(button.dataset.epi)); const modal=dialog(epi.name);const content=modal.querySelector('[data-content]');
          content.innerHTML=`<dl>${epiFields.map(([key,labelKey,label])=>`<dt data-i18n="${labelKey}">${esc(tr(labelKey,label))}</dt><dd${epi[key] ? '' : ' data-i18n="safetyLibrary.notProvided"'}>${key==='ca_expiry' && epi[key] ? (globalThis.EpiI18n?.bindText?.('safetyLibrary.value',{value:epi[key]},'{value}',{value:{type:'date',value:epi[key]}}) ?? esc(epi[key])) : esc(epi[key] || tr('safetyLibrary.notProvided','Não informado'))}</dd>`).join('')}</dl><div data-photo></div><h3 data-i18n="ui.safety_library.documentos_associados_311089">Documentos associados</h3><div data-related></div><p data-library-status></p>`;
          const related=documents.filter(d=>d.epi_ids.includes(epi.id));
          documentRows(content.querySelector('[data-related]'),related,request);
          if(epi.has_photo){try{
            const blob=await request('photo',{epi_id:epi.id},true);if(!modal.isConnected){return;}
            const photoUrl=URL.createObjectURL(blob);modal.addEventListener('close',()=>URL.revokeObjectURL(photoUrl));
            const image=document.createElement('img');image.src=photoUrl;image.alt=epi.name;image.className='safety-epi-photo';content.querySelector('[data-photo]').append(image);
            image.onclick=()=>{image.classList.toggle('enlarged');};
          }catch(e){status(content,e,true);}}
        };});
      };
      approvedRoot.querySelectorAll('input').forEach(input=>{input.oninput=paint;});paint();
      libraryRoot.innerHTML=`<h3 data-i18n="ui.sidebar.biblioteca_de_seguranca_795807">Biblioteca de Segurança</h3><p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.unidade_de_consulta_p0_c6e110',{p0:(docsResult.context.unit_name)},'Unidade de consulta: {p0}') ?? `Unidade de consulta: ${esc(docsResult.context.unit_name)}`)}</p><div class="safety-filters"><input data-search type="search" aria-label="Pesquisar documentos" placeholder="Pesquisar título, versão ou EPI" data-i18n-placeholder="ui.safety_library.pesquisar_titulo_versao_ou_epi_f1853e" data-i18n-aria-label="ui.safety_library.pesquisar_documentos_b222d2"><select data-category aria-label="Categoria" data-i18n-aria-label="ui.safety_library.categoria_54276a"><option value="" data-i18n="ui.safety_library.todas_as_categorias_9e7533">Todas as categorias</option>${Object.entries(categories).map(([id,label])=>option(id,label,'safetyLibrary.category.'+id)).join('')}</select><select data-related-epi aria-label="EPI relacionado" data-i18n-aria-label="ui.safety_library.epi_relacionado_b42393"><option value="" data-i18n="stock.pendingReg.allEpis">Todos os EPIs</option>${epis.map(e=>option(e.id,e.name)).join('')}</select></div><div data-documents></div>`;
      const filterDocuments=()=>{
        const query=libraryRoot.querySelector('[data-search]').value.toLocaleLowerCase();const cat=libraryRoot.querySelector('[data-category]').value;const epi=Number(libraryRoot.querySelector('[data-related-epi]').value);
        documentRows(libraryRoot.querySelector('[data-documents]'),documents.filter(d=>(!cat||cat===d.category)&&(!epi||d.epi_ids.includes(epi))&&(`${d.title} ${d.version_label} ${d.epi_ids.map(id=>epis.find(e=>e.id===id)?.name||'').join(' ')}`).toLocaleLowerCase().includes(query)),request,epis);
      };
      libraryRoot.querySelectorAll('input,select').forEach(f=>{f.oninput=filterDocuments;});filterDocuments();
    } catch(e) {[approvedRoot,libraryRoot].forEach(root=>{const message=e.i18n;root.textContent=message?.key ? (globalThis.EpiI18n?.textFor?.(root,message.key,message.text,message.vars,message.refs) ?? message.text) : e.message;});}
  }
  function documentRows(root, documents, request, epis=[]) {
    root.innerHTML=documents.length ? `<div class="safety-documents">${documents.map(d=>`<article class="safety-card"><h4>${esc(d.title)}</h4><p${categories[d.category] ? ` data-i18n="safetyLibrary.category.${esc(d.category)}"` : ''}>${esc(categories[d.category] || d.category_label)}</p><p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.versao_p2_vigencia_p3_982bcf',{p2:(d.version_label),p3:(d.effective_date)},'Vers\u00e3o {p2} \u00b7 Vig\u00eancia {p3}',{p3:{type:'date',value:d.effective_date}}) ?? `Versão ${esc(d.version_label)} · Vigência ${esc(d.effective_date)}`)}</p><p>${esc(d.epi_ids.map(id=>epis.find(e=>e.id===id)?.name || `EPI #${id}`).join(', '))}</p><button data-document="${d.id}" data-i18n="ui.compras.visualizar_1acb4b">Visualizar</button></article>`).join('')}</div>` : '<p data-i18n="ui.safety_library.nenhum_documento_publicado_e_autorizado_neste_contexto_233781">Nenhum documento publicado e autorizado neste contexto.</p>';
    root.querySelectorAll('[data-document]').forEach(b=>{b.onclick=()=>viewer(request,documents.find(d=>d.id===Number(b.dataset.document)));});
  }
  async function admin(root) {
    const request=client();
    root.innerHTML='<p role="status" data-i18n="ui.safety_library.carregando_gestao_documental_e2ff66">Carregando gest\u00e3o documental\u2026</p>';
    try {
      const [options, listing] = await Promise.all([request('options'),request('documents')]);
      const versions=listing.items;
      root.innerHTML=`<h2 data-i18n="ui.sidebar.biblioteca_de_seguranca_795807">Biblioteca de Segurança</h2><p data-i18n="ui.safety_library.somente_administrador_geral_e_administrador_de_registro_podem_gerir_documen_166bdd">Somente Administrador Geral e Administrador de Registro podem gerir documentos. Originais permanecem privados; versões substituídas preservam o histórico.</p>
        <form data-upload class="safety-upload"><label data-i18n="ui.safety_library.documento_a_versionar_26474b">Documento a versionar<select name="document_id"><option value="" data-i18n="ui.safety_library.novo_documento_5dcc24">Novo documento</option>${[...new Map(versions.filter(v=>v.state!=='archived').map(v=>[v.document_id,v])).values()].map(d=>option(d.document_id,d.title)).join('')}</select></label>
        <label data-i18n="ui.compras.titulo_4c08a5">Título<input name="title" required maxlength="240"></label><label data-i18n="ui.safety_library.categoria_54276a">Categoria<select name="category">${Object.entries(categories).map(([id,label])=>option(id,label,'safetyLibrary.category.'+id)).join('')}</select></label>
        <label data-i18n="ui.safety_library.versao_15116b">Versão<input name="version_label" required maxlength="80"></label><label data-i18n="ui.safety_library.data_de_vigencia_379ff3">Data de vigência<input type="date" name="effective_date" required></label>
        <label data-i18n="ui.safety_library.todas_as_unidades_da_empresa_d4cf3a"><input name="all_units" type="checkbox"> Todas as unidades da empresa</label><label data-i18n="ui.safety_library.unidades_selecao_multipla_174e10">Unidades (seleção múltipla)<select name="unit_ids" multiple>${options.units.map(u=>option(u.id,u.name)).join('')}</select></label>
        <label data-i18n="ui.safety_library.epis_relacionados_f5d3cc">EPIs relacionados<select name="epi_ids" multiple>${options.epis.map(e=>option(e.id,e.name)).join('')}</select></label><label data-i18n="ui.safety_library.setores_separados_por_virgula_vazio_todos_a1cf6f">Setores (separados por vírgula; vazio = todos)<input name="sectors"></label><label data-i18n="ui.safety_library.atividades_funcoes_separadas_por_virgula_vazio_todas_08a895">Atividades/funções (separadas por vírgula; vazio = todas)<input name="activities"></label>
        <label data-i18n="ui.safety_library.arquivo_ate_20_mib_3fa4be">Arquivo (até 20 MiB)<input type="file" name="file" accept=".pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg" required></label><button type="submit" data-i18n="ui.safety_library.cadastrar_versao_em_rascunho_1edb80">Cadastrar versão em rascunho</button></form>
        <p data-library-status role="status"></p><label data-i18n="ui.safety_library.permitir_download_de_originais_aos_dois_perfis_administradores_autorizados_c2ac85"><input data-policy type="checkbox" ${options.allow_admin_original_download?'checked':''}> Permitir download de originais aos dois perfis administradores autorizados</label>
        <div class="safety-filters"><input data-search type="search" placeholder="Pesquisar documentos e versões" aria-label="Pesquisar documentos e versões" data-i18n-placeholder="ui.safety_library.pesquisar_documentos_e_versoes_e0dd08" data-i18n-aria-label="ui.safety_library.pesquisar_documentos_e_versoes_e0dd08"><select data-category aria-label="Categoria" data-i18n-aria-label="ui.safety_library.categoria_54276a"><option value="" data-i18n="ui.safety_library.todas_as_categorias_9e7533">Todas as categorias</option>${Object.entries(categories).map(([id,label])=>option(id,label,'safetyLibrary.category.'+id)).join('')}</select></div><div data-versions></div>`;
      const form=root.querySelector('[data-upload]');
      form.elements.all_units.onchange=()=>{form.elements.unit_ids.disabled=form.elements.all_units.checked;};
      form.onsubmit=async event=>{
        event.preventDefault();const submit=form.querySelector('button[type=submit]');submit.disabled=true;status(root,(globalThis.trEpi?.('ui.safety_library.validando_arquivo_e_gerando_pre_visualizacao_segura_7364a1','Validando arquivo e gerando pr\u00e9-visualiza\u00e7\u00e3o segura\u2026',{}) ?? 'Validando arquivo e gerando pr\u00e9-visualiza\u00e7\u00e3o segura\u2026'),false,{key:'ui.safety_library.validando_arquivo_e_gerando_pre_visualizacao_segura_7364a1',vars:{}});
        try {
          const file=form.elements.file.files[0];if(!file||file.size>20*1024*1024){throw new Error((globalThis.trEpi?.('ui.safety_library.selecione_um_arquivo_de_ate_20_mib_e84d18','Selecione um arquivo de at\u00e9 20 MiB.',{}) ?? 'Selecione um arquivo de at\u00e9 20 MiB.'));}
          const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file);});
          const ext=file.name.split('.').pop().toLowerCase();const mimes={pdf:'application/pdf',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',xls:'application/vnd.ms-excel',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg'};
          const arrays=name=>[...form.elements[name].selectedOptions].map(o=>Number(o.value));
          const data={title:form.elements.title.value,category:form.elements.category.value,version_label:form.elements.version_label.value,effective_date:form.elements.effective_date.value,all_units:form.elements.all_units.checked,unit_ids:form.elements.all_units.checked?[]:arrays('unit_ids'),epi_ids:arrays('epi_ids'),sectors:form.elements.sectors.value.split(',').map(s=>s.trim()).filter(Boolean),activities:form.elements.activities.value.split(',').map(s=>s.trim()).filter(Boolean),filename:file.name,mime:mimes[ext],content_base64:String(dataUrl).split(',')[1],idempotency_key:crypto.randomUUID().replace(/-/g,'')};
          if(form.elements.document_id.value){data.document_id=Number(form.elements.document_id.value);}
          await request('upload',data);await admin(root);
        }catch(e){status(root,(globalThis.trEpi?.('ui.safety_library.cadastro_recusado_p0_e8bad4','Cadastro recusado: {p0}',{p0:(e.message)}) ?? `Cadastro recusado: ${e.message}`),true,{key:'ui.safety_library.cadastro_recusado_p0_e8bad4',vars:{p0:(e.message)},refs:(e.i18n?.key ? {p0:{type:'message',key:e.i18n.key,vars:e.i18n.vars,refs:e.i18n.refs}} : {})});submit.disabled=false;}
      };
      root.querySelector('[data-policy]').onchange=async event=>{
        const checkbox=event.target;const justification=globalThis.prompt((globalThis.trEpi?.('ui.safety_library.justificativa_da_alteracao_da_politica_de_download_administrativo_ba004f','Justificativa da altera\u00e7\u00e3o da pol\u00edtica de download administrativo:',{}) ?? 'Justificativa da altera\u00e7\u00e3o da pol\u00edtica de download administrativo:'));
        if(!justification){checkbox.checked=!checkbox.checked;return;}
        try{await request('policy',{allow_admin_original_download:checkbox.checked,justification});status(root,(globalThis.trEpi?.('ui.safety_library.politica_registrada_colaboradores_continuam_sem_acesso_a_originais_787643','Pol\u00edtica registrada. Colaboradores continuam sem acesso a originais.',{}) ?? 'Pol\u00edtica registrada. Colaboradores continuam sem acesso a originais.'),false,{key:'ui.safety_library.politica_registrada_colaboradores_continuam_sem_acesso_a_originais_787643',vars:{}});}catch(e){checkbox.checked=!checkbox.checked;status(root,e,true);}
      };
      const paint=()=>{
        const query=root.querySelector('[data-search]').value.toLocaleLowerCase(),category=root.querySelector('[data-category]').value;
        const target=root.querySelector('[data-versions]');const filtered=versions.filter(d=>(!category||d.category===category)&&(`${d.title} ${d.version_label}`).toLocaleLowerCase().includes(query));
        target.innerHTML=filtered.map(d=>`<article class="safety-card"><h3>${esc(d.title)}</h3><p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.p1_versao_p2_revisao_p3_p4_vigencia_p5_0da9b0',{p1:(categories[d.category]),p2:(d.version_label),p3:(d.revision),p4:(tr('safetyLibrary.state.' + d.state, d.state_label)),p5:(d.effective_date)},'{p1} \u00b7 Vers\u00e3o {p2} / revis\u00e3o {p3} \u00b7 {p4} \u00b7 Vig\u00eancia {p5}',{p1:'safetyLibrary.category.'+d.category,p4:'safetyLibrary.state.'+d.state,p5:{type:'date',value:d.effective_date}}) ?? `${esc(categories[d.category])} · Versão ${esc(d.version_label)} / revisão ${d.revision} · ${esc(tr('safetyLibrary.state.' + d.state, d.state_label))} · Vigência ${esc(d.effective_date)}`)}</p><p>${d.all_units?'<span data-i18n="ui.modals.todas_as_unidades_94b398">Todas as unidades</span>':esc(d.unit_ids.map(id=>options.units.find(u=>u.id===id)?.name||id).join(', '))}</p><button data-preview="${d.id}" data-i18n="ui.compras.visualizar_1acb4b">Visualizar</button> ${d.state==='draft'?`<button data-publish="${d.id}" data-i18n="ui.safety_library.publicar_326fdf">Publicar</button>`:''} ${d.state!=='archived'?`<button data-archive="${d.id}" data-i18n="ui.safety_library.arquivar_documento_000f59">Arquivar documento</button>`:''} <button data-history="${d.id}" data-i18n="dataMigration.historyTab">Histórico</button></article>`).join('')||'<p data-i18n="ui.safety_library.nenhum_documento_cadastrado_51e2d0">Nenhum documento cadastrado.</p>';
        target.querySelectorAll('button').forEach(button=>{button.onclick=async()=>{
          const kind=['preview','publish','archive','history'].find(k=>button.dataset[k]);const d=versions.find(v=>v.id===Number(button.dataset[kind]));
          try{
            if(kind==='preview'){return await viewer(request,d);}
            if(kind==='history'){const h=await request('history',{document_id:d.document_id});const modal=dialog((globalThis.trEpi?.('ui.safety_library.historico_documental_01da7d','Hist\u00f3rico documental',{}) ?? 'Hist\u00f3rico documental'),'ui.safety_library.historico_documental_01da7d');modal.querySelector('[data-content]').innerHTML=h.items.map(e=>`<p>${(globalThis.EpiI18n?.bindText?.('ui.safety_library.p0_p1_ator_p2_p3_152f99',{p0:(e.created_at),p1:(e.action),p2:(e.actor_user_id||e.employee_id||''),p3:(e.details)},'{p0} \u00b7 {p1} \u00b7 ator {p2} \u00b7 {p3}') ?? `${esc(e.created_at)} · ${esc(e.action)} · ator ${esc(e.actor_user_id||e.employee_id||'')} · ${esc(e.details)}`)}</p>`).join('')||'<p data-i18n="ui.safety_library.sem_eventos_78127d">Sem eventos.</p>';return;}
            const justification=globalThis.prompt((globalThis.trEpi?.('ui.safety_library.justificativa_obrigatoria_cf8463','Justificativa obrigat\u00f3ria:',{}) ?? 'Justificativa obrigat\u00f3ria:'));if(!justification){return;}
            await request(kind,{document_id:d.document_id,version_id:d.id,justification});await admin(root);
          }catch(e){status(root,e,true);}
        };});
      };
      root.querySelectorAll('[data-search],[data-category]').forEach(f=>{f.oninput=paint;});paint();
    }catch(e){root.textContent=((globalThis.EpiI18n?.textFor?.(root,'ui.safety_library.gestao_documental_indisponivel_p0_d1fb93','Gest\u00e3o documental indispon\u00edvel: {p0}',{p0:(e.message)},e.i18n?.key ? {p0:{type:'message',key:e.i18n.key,vars:e.i18n.vars,refs:e.i18n.refs}} : {}) ?? globalThis.trEpi?.('ui.safety_library.gestao_documental_indisponivel_p0_d1fb93','Gest\u00e3o documental indispon\u00edvel: {p0}',{p0:(e.message)})) ?? `Gestão documental indisponível: ${e.message}`);}
  }
  globalThis.SafetyLibrary = Object.freeze({portal, admin});
})();
