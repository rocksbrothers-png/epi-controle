/* Private library: credentials stay in closures; only authorized PNG pages are displayed. */
(() => {
  'use strict';
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const categories = {
    epi_matrix:'Matriz de Aplicação de EPIs', glove_matrix:'Matriz de Seleção de Luvas',
    care_guides:'Guias de Higienização e Conservação', use_instructions:'Instruções de Uso dos EPIs',
    technical_manuals:'Manuais e Fichas Técnicas', other_sst:'Outros Documentos de SST'
  };
  const option = (id, label) => `<option value="${esc(id)}">${esc(label)}</option>`;
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
        throw new Error(typeof error.error === 'string' ? error.error : 'Acesso à biblioteca recusado.');
      }
      return bytes ? response.blob() : response.json();
    };
  }
  function status(root, message, error = false) {
    const node = root.querySelector('[data-library-status]');
    if (node) { node.textContent = message; node.setAttribute('role',error ? 'alert':'status'); }
  }
  function dialog(title) {
    const node = document.createElement('dialog');
    node.className = 'safety-dialog';
    node.innerHTML = `<header><h2>${esc(title)}</h2><button type="button" data-close aria-label="Fechar">Fechar</button></header><div data-content></div>`;
    document.body.append(node);
    node.querySelector('[data-close]').onclick = () => node.close();
    node.addEventListener('close', () => node.remove());
    node.showModal();
    return node;
  }
  async function viewer(request, document) {
    const modal = dialog(document.title);
    const content = modal.querySelector('[data-content]');
    content.innerHTML = '<p role="status">Carregando pré-visualização…</p>';
    let url;
    let sequence = 0;
    modal.addEventListener('close', () => { sequence++; if(url) {URL.revokeObjectURL(url);} });
    try {
      const result = await request('manifest',{document_id:document.document_id,version_id:document.id});
      if (!modal.isConnected) {return;}
      const parts = result.preview.parts;
      let part = 0, page = 0, scale = 1;
      content.innerHTML = `<p>Versão ${esc(document.version_label)} · Vigência ${esc(document.effective_date)}</p>
        ${(result.preview.warnings || []).map(w => `<p role="note">${esc(w)}</p>`).join('')}
        <div class="safety-viewer-tools"><label>Aba <select data-part>${parts.map(p=>option(p.index,p.name)).join('')}</select></label>
        <button data-prev>Anterior</button><span data-counter></span><button data-next>Próxima</button>
        <button data-less aria-label="Diminuir zoom">−</button><span data-zoom>100%</span><button data-more aria-label="Aumentar zoom">+</button><button data-fit>Ajustar</button></div>
        <p data-library-status role="status"></p><div class="safety-page-viewport"><img data-page draggable="false" alt="Pré-visualização do documento"></div>`;
      const image = content.querySelector('[data-page]');
      image.oncontextmenu = event => event.preventDefault();
      const zoom = () => {image.style.width = `${scale * 100}%`; content.querySelector('[data-zoom]').textContent=`${Math.round(scale*100)}%`;};
      const load = async () => {
        const current = ++sequence;
        status(content,'Carregando página…'); image.hidden = true;
        content.querySelector('[data-counter]').textContent = `${page+1} / ${parts[part].pages.length}`;
        content.querySelector('[data-prev]').disabled = page===0;
        content.querySelector('[data-next]').disabled = page===parts[part].pages.length-1;
        try {
          const blob = await request('page',{document_id:document.document_id,version_id:document.id,part_index:part,page_index:page},true);
          if(current!==sequence || !modal.isConnected) {return;}
          if(url) {URL.revokeObjectURL(url);}
          url=URL.createObjectURL(blob);image.src=url;image.hidden=false;zoom();status(content,'');
        } catch(e) { if(current===sequence) {status(content,e.message,true);} }
      };
      content.querySelector('[data-part]').onchange=e=>{part=Number(e.target.value);page=0;scale=1;void load();};
      content.querySelector('[data-prev]').onclick=()=>{page--;void load();};
      content.querySelector('[data-next]').onclick=()=>{page++;void load();};
      content.querySelector('[data-less]').onclick=()=>{scale=Math.max(.5,scale-.25);zoom();};
      content.querySelector('[data-more]').onclick=()=>{scale=Math.min(4,scale+.25);zoom();};
      content.querySelector('[data-fit]').onclick=()=>{scale=1;zoom();};
      await load();
    } catch(e) {content.textContent=`Pré-visualização indisponível: ${e.message}`;}
  }
  const epiFields = [
    ['name','EPI'],['manufacturer','Fabricante'],['model_reference','Modelo/referência'],['ca','CA'],
    ['ca_expiry','Validade do CA'],['manufacturer_validity_months','Vida útil (meses)'],
    ['sector','Proteção'],['epi_section','Seção'],['manufacturer_recommendations','Recomendações/restrições']
  ];
  function catalogueMarkup(items) {
    const value = (item,key) => key==='manufacturer_validity_months' && !item[key] ? 'Não informada' : (item[key] || 'Não informado');
    return `<div class="safety-desktop"><table><thead><tr>${epiFields.map(([,label])=>`<th>${label}</th>`).join('')}<th>Foto</th><th>Detalhes</th></tr></thead><tbody>
      ${items.map(e=>`<tr>${epiFields.map(([key])=>`<td>${esc(value(e,key))}</td>`).join('')}<td>${e.has_photo?`<span data-catalogue-photo="${e.id}"></span>`:'Sem foto'}</td><td><button data-epi="${e.id}">Ver EPI</button></td></tr>`).join('')}</tbody></table></div>
      <div class="safety-mobile">${items.map(e=>`<article class="safety-card"><h3>${esc(e.name)}</h3>${e.has_photo?`<span data-catalogue-photo="${e.id}"></span>`:''}<p>${esc(e.manufacturer)} · CA ${esc(e.ca)}</p><p>${esc(e.sector)}</p><button data-epi="${e.id}">Ver EPI e documentos</button></article>`).join('')}</div>`;
  }
  async function portal(approvedRoot, libraryRoot, credentials) {
    const request = client(credentials);
    approvedRoot.innerHTML='<p role="status">Carregando catálogo aprovado…</p>';
    libraryRoot.innerHTML='<p role="status">Carregando biblioteca…</p>';
    try {
      const [episResult, docsResult] = await Promise.all([request('approved-epis'),request('documents')]);
      const epis = episResult.items, documents = docsResult.items;
      const photos = new Map();
      const photoUrls = [];
      globalThis.addEventListener('pagehide', () => photoUrls.forEach(url=>URL.revokeObjectURL(url)), {once:true});
      approvedRoot.innerHTML=`<h3>EPIs Aprovados</h3><p>Aprovação cadastral da empresa. A validade do CA não é a validade física de um lote; este catálogo não informa disponibilidade para entrega.</p>
        <div class="safety-filters">${[['name','Nome do EPI'],['sector','Proteção'],['ca','CA'],['manufacturer','Fabricante'],['epi_section','Seção']].map(([key,label])=>`<input type="search" data-epi-filter="${key}" aria-label="${label}" placeholder="Buscar por ${label}">`).join('')}</div><div data-epis></div>`;
      const paint = () => {
        const filtered = epis.filter(e=>[...approvedRoot.querySelectorAll('[data-epi-filter]')].every(f=>String(e[f.dataset.epiFilter]||'').toLocaleLowerCase().includes(f.value.trim().toLocaleLowerCase())));
        const target=approvedRoot.querySelector('[data-epis]'); target.innerHTML=filtered.length ? catalogueMarkup(filtered) : '<p>Nenhum EPI aprovado neste contexto.</p>';
        target.querySelectorAll('[data-catalogue-photo]').forEach(async node=>{
          const id=Number(node.dataset.cataloguePhoto);
          try{
            if(!photos.has(id)){photos.set(id,request('photo',{epi_id:id},true).then(blob=>{const url=URL.createObjectURL(blob);photoUrls.push(url);return url;}));}
            const url=await photos.get(id);if(!node.isConnected){return;}
            const image=document.createElement('img');image.src=url;image.alt='Foto do EPI';image.style.width='64px';image.style.height='64px';image.style.objectFit='contain';image.oncontextmenu=event=>event.preventDefault();node.append(image);
          }catch{node.textContent='Foto indisponível';}
        });
        target.querySelectorAll('[data-epi]').forEach(button=>{button.onclick=async()=>{
          const epi=epis.find(e=>e.id===Number(button.dataset.epi)); const modal=dialog(epi.name);const content=modal.querySelector('[data-content]');
          content.innerHTML=`<dl>${epiFields.map(([key,label])=>`<dt>${label}</dt><dd>${esc(epi[key] || 'Não informado')}</dd>`).join('')}</dl><div data-photo></div><h3>Documentos associados</h3><div data-related></div><p data-library-status></p>`;
          const related=documents.filter(d=>d.epi_ids.includes(epi.id));
          documentRows(content.querySelector('[data-related]'),related,request);
          if(epi.has_photo){try{
            const blob=await request('photo',{epi_id:epi.id},true);if(!modal.isConnected){return;}
            const photoUrl=URL.createObjectURL(blob);modal.addEventListener('close',()=>URL.revokeObjectURL(photoUrl));
            const image=document.createElement('img');image.src=photoUrl;image.alt=epi.name;image.className='safety-epi-photo';content.querySelector('[data-photo]').append(image);
            image.onclick=()=>{image.classList.toggle('enlarged');};
          }catch(e){status(content,e.message,true);}}
        };});
      };
      approvedRoot.querySelectorAll('input').forEach(input=>{input.oninput=paint;});paint();
      libraryRoot.innerHTML=`<h3>Biblioteca de Segurança</h3><p>Unidade de consulta: ${esc(docsResult.context.unit_name)}</p><div class="safety-filters"><input data-search type="search" aria-label="Pesquisar documentos" placeholder="Pesquisar título, versão ou EPI"><select data-category aria-label="Categoria"><option value="">Todas as categorias</option>${Object.entries(categories).map(([id,label])=>option(id,label)).join('')}</select><select data-related-epi aria-label="EPI relacionado"><option value="">Todos os EPIs</option>${epis.map(e=>option(e.id,e.name)).join('')}</select></div><div data-documents></div>`;
      const filterDocuments=()=>{
        const query=libraryRoot.querySelector('[data-search]').value.toLocaleLowerCase();const cat=libraryRoot.querySelector('[data-category]').value;const epi=Number(libraryRoot.querySelector('[data-related-epi]').value);
        documentRows(libraryRoot.querySelector('[data-documents]'),documents.filter(d=>(!cat||cat===d.category)&&(!epi||d.epi_ids.includes(epi))&&(`${d.title} ${d.version_label} ${d.epi_ids.map(id=>epis.find(e=>e.id===id)?.name||'').join(' ')}`).toLocaleLowerCase().includes(query)),request,epis);
      };
      libraryRoot.querySelectorAll('input,select').forEach(f=>{f.oninput=filterDocuments;});filterDocuments();
    } catch(e) {approvedRoot.textContent=e.message;libraryRoot.textContent=e.message;}
  }
  function documentRows(root, documents, request, epis=[]) {
    root.innerHTML=documents.length ? `<div class="safety-documents">${documents.map(d=>`<article class="safety-card"><h4>${esc(d.title)}</h4><p>${esc(d.category_label || categories[d.category])}</p><p>Versão ${esc(d.version_label)} · Vigência ${esc(d.effective_date)}</p><p>${esc(d.epi_ids.map(id=>epis.find(e=>e.id===id)?.name || `EPI #${id}`).join(', '))}</p><button data-document="${d.id}">Visualizar</button></article>`).join('')}</div>` : '<p>Nenhum documento publicado e autorizado neste contexto.</p>';
    root.querySelectorAll('[data-document]').forEach(b=>{b.onclick=()=>viewer(request,documents.find(d=>d.id===Number(b.dataset.document)));});
  }
  async function admin(root) {
    const request=client();
    root.innerHTML='<p role="status">Carregando gestão documental…</p>';
    try {
      const [options, listing] = await Promise.all([request('options'),request('documents')]);
      const versions=listing.items;
      root.innerHTML=`<h2>Biblioteca de Segurança</h2><p>Somente Administrador Geral e Administrador de Registro podem gerir documentos. Originais permanecem privados; versões substituídas preservam o histórico.</p>
        <form data-upload class="safety-upload"><label>Documento a versionar<select name="document_id"><option value="">Novo documento</option>${[...new Map(versions.filter(v=>v.state!=='archived').map(v=>[v.document_id,v])).values()].map(d=>option(d.document_id,d.title)).join('')}</select></label>
        <label>Título<input name="title" required maxlength="240"></label><label>Categoria<select name="category">${Object.entries(categories).map(([id,label])=>option(id,label)).join('')}</select></label>
        <label>Versão<input name="version_label" required maxlength="80"></label><label>Data de vigência<input type="date" name="effective_date" required></label>
        <label><input name="all_units" type="checkbox"> Todas as unidades da empresa</label><label>Unidades (seleção múltipla)<select name="unit_ids" multiple>${options.units.map(u=>option(u.id,u.name)).join('')}</select></label>
        <label>EPIs relacionados<select name="epi_ids" multiple>${options.epis.map(e=>option(e.id,e.name)).join('')}</select></label><label>Setores (separados por vírgula; vazio = todos)<input name="sectors"></label><label>Atividades/funções (separadas por vírgula; vazio = todas)<input name="activities"></label>
        <label>Arquivo (até 20 MiB)<input type="file" name="file" accept=".pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg" required></label><button type="submit">Cadastrar versão em rascunho</button></form>
        <p data-library-status role="status"></p><label><input data-policy type="checkbox" ${options.allow_admin_original_download?'checked':''}> Permitir download de originais aos dois perfis administradores autorizados</label>
        <div class="safety-filters"><input data-search type="search" placeholder="Pesquisar documentos e versões" aria-label="Pesquisar documentos e versões"><select data-category aria-label="Categoria"><option value="">Todas as categorias</option>${Object.entries(categories).map(([id,label])=>option(id,label)).join('')}</select></div><div data-versions></div>`;
      const form=root.querySelector('[data-upload]');
      form.elements.all_units.onchange=()=>{form.elements.unit_ids.disabled=form.elements.all_units.checked;};
      form.onsubmit=async event=>{
        event.preventDefault();const submit=form.querySelector('button[type=submit]');submit.disabled=true;status(root,'Validando arquivo e gerando pré-visualização segura…');
        try {
          const file=form.elements.file.files[0];if(!file||file.size>20*1024*1024){throw new Error('Selecione um arquivo de até 20 MiB.');}
          const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file);});
          const ext=file.name.split('.').pop().toLowerCase();const mimes={pdf:'application/pdf',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',xls:'application/vnd.ms-excel',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg'};
          const arrays=name=>[...form.elements[name].selectedOptions].map(o=>Number(o.value));
          const data={title:form.elements.title.value,category:form.elements.category.value,version_label:form.elements.version_label.value,effective_date:form.elements.effective_date.value,all_units:form.elements.all_units.checked,unit_ids:form.elements.all_units.checked?[]:arrays('unit_ids'),epi_ids:arrays('epi_ids'),sectors:form.elements.sectors.value.split(',').map(s=>s.trim()).filter(Boolean),activities:form.elements.activities.value.split(',').map(s=>s.trim()).filter(Boolean),filename:file.name,mime:mimes[ext],content_base64:String(dataUrl).split(',')[1],idempotency_key:crypto.randomUUID().replace(/-/g,'')};
          if(form.elements.document_id.value){data.document_id=Number(form.elements.document_id.value);}
          await request('upload',data);await admin(root);
        }catch(e){status(root,`Cadastro recusado: ${e.message}`,true);submit.disabled=false;}
      };
      root.querySelector('[data-policy]').onchange=async event=>{
        const checkbox=event.target;const justification=globalThis.prompt('Justificativa da alteração da política de download administrativo:');
        if(!justification){checkbox.checked=!checkbox.checked;return;}
        try{await request('policy',{allow_admin_original_download:checkbox.checked,justification});status(root,'Política registrada. Colaboradores continuam sem acesso a originais.');}catch(e){checkbox.checked=!checkbox.checked;status(root,e.message,true);}
      };
      const paint=()=>{
        const query=root.querySelector('[data-search]').value.toLocaleLowerCase(),category=root.querySelector('[data-category]').value;
        const target=root.querySelector('[data-versions]');const filtered=versions.filter(d=>(!category||d.category===category)&&(`${d.title} ${d.version_label}`).toLocaleLowerCase().includes(query));
        target.innerHTML=filtered.map(d=>`<article class="safety-card"><h3>${esc(d.title)}</h3><p>${esc(categories[d.category])} · Versão ${esc(d.version_label)} / revisão ${d.revision} · ${esc(d.state_label)} · Vigência ${esc(d.effective_date)}</p><p>${d.all_units?'Todas as unidades':esc(d.unit_ids.map(id=>options.units.find(u=>u.id===id)?.name||id).join(', '))}</p><button data-preview="${d.id}">Visualizar</button> ${d.state==='draft'?`<button data-publish="${d.id}">Publicar</button>`:''} ${d.state!=='archived'?`<button data-archive="${d.id}">Arquivar documento</button>`:''} <button data-history="${d.id}">Histórico</button></article>`).join('')||'<p>Nenhum documento cadastrado.</p>';
        target.querySelectorAll('button').forEach(button=>{button.onclick=async()=>{
          const kind=['preview','publish','archive','history'].find(k=>button.dataset[k]);const d=versions.find(v=>v.id===Number(button.dataset[kind]));
          try{
            if(kind==='preview'){return await viewer(request,d);}
            if(kind==='history'){const h=await request('history',{document_id:d.document_id});const modal=dialog('Histórico documental');modal.querySelector('[data-content]').innerHTML=h.items.map(e=>`<p>${esc(e.created_at)} · ${esc(e.action)} · ator ${esc(e.actor_user_id||e.employee_id||'')} · ${esc(e.details)}</p>`).join('')||'<p>Sem eventos.</p>';return;}
            const justification=globalThis.prompt('Justificativa obrigatória:');if(!justification){return;}
            await request(kind,{document_id:d.document_id,version_id:d.id,justification});await admin(root);
          }catch(e){status(root,e.message,true);}
        };});
      };
      root.querySelectorAll('[data-search],[data-category]').forEach(f=>{f.oninput=paint;});paint();
    }catch(e){root.textContent=`Gestão documental indisponível: ${e.message}`;}
  }
  globalThis.SafetyLibrary = Object.freeze({portal, admin});
})();
