'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm');
const source=fs.readFileSync(path.resolve(__dirname,'../../app.js'),'utf8');
function functionSource(name) {
  const start=new RegExp('^(?:async )?function '+name+'\\(','m').exec(source);
  if(!start) throw new Error(name);
  const end=source.slice(start.index+start[0].length).search(/^}/m);
  return source.slice(start.index,start.index+start[0].length+end+1);
}
function harness() {
  const nodes=new Map(),sent=[],toasts=[];let overlay,rows={};
  const node=(id)=>{
    if(!nodes.has(id)) nodes.set(id,{id,value:'',checked:false,dataset:{},style:{},listeners:{},textContent:'',disabled:false,
      querySelector(selector){
        const row=selector.match(/^\[data-conferencia-row="([^"]+)"\]/);if(row)return rows[row[1]].row;
        const check=selector.match(/^\[data-conferencia-item\]\[value="([^"]+)"\]/);if(check)return rows[check[1]].checkbox;
        return node(selector);
      },
      querySelectorAll(selector){
        if(selector==='[data-conferencia-item]')return Object.values(rows).map(r=>r.checkbox);
        if(selector==='[data-conferencia-capture]')return Object.values(rows).map(r=>r.capture);
        return [];
      },remove(){this.removed=true;},
      set innerHTML(html){this.html=html;if(html.includes('data-conferencia-row=')) {
        rows={};for(const match of html.matchAll(/data-conferencia-row="([^"]+)" data-eff-qty="([^"]+)"/g)) {
          const row={style:{},getAttribute:()=>match[2]};
          const checkbox={value:match[1],checked:true,closest:()=>row};
          rows[match[1]]={row,checkbox,capture:{dataset:{conferenciaCapture:match[1]},listeners:{}}};
        }
      }},get innerHTML(){return this.html||'';}
    });
    return nodes.get(id);
  };
  const context={console,URLSearchParams,Map,Array,Date,CSS:{escape:String},state:{user:{id:1}},
    document:{getElementById:()=>null,createElement:()=>{overlay=node('overlay-'+nodes.size);return overlay;},body:{appendChild(){}},querySelectorAll:()=>[]},
    esc:s=>String(s??''),tr:(_key,fallback,params={})=>fallback.replace(/\{(\w+)\}/g,(m,k)=>params[k]??m),
    bindAppListener:(target,event,callback)=>{if(target){target.listeners ||= {};target.listeners[event]=callback;}},
    FileReader:class{readAsDataURL(file){this.result='data:'+file.type+';base64,'+(file.data||'iVBORw0KGgo=');this.onload();}},
    api:async(url,options)=>{sent.push({url,body:JSON.parse(options.body)});return{manufacture_date:'2024-01-02',physical_expiry_date:'2032-01-02',candidates:[]};},
    showToast:(...args)=>toasts.push(args),openPoDetail:async()=>{},loadPurchaseOrders:()=>{}
  };
  vm.createContext(context);
  const names=['readStockEvidenceFile','readReceiptLotPhoto','receiptLotCapturePayload','applyReceiptDateSuggestions',
    'openReceiptLotCaptureModal','openConferenciaModal','submitPoReceive','readManufacturerValidityFromImage'];
  vm.runInContext(names.map(functionSource).join('\n'),context);
  return{context,node,sent,toasts,get overlay(){return overlay;},get rows(){return rows;},run:code=>vm.runInContext(code,context)};
}
const photo={name:'etiqueta.png',type:'image/png',size:100};
const proof={capture_version:1,quantity:2,lot_code:'REAL',manufacture_date:'2024-01-02',manufacturer_validity_date:'2032-01-02',
  expiry_source:'label',evidence:'Etiqueta REAL',evidence_file:{filename:'etiqueta.png'},physical_lot_confirmed:true};
module.exports=({testAsync,assert,eq})=>{
  testAsync('Compras: uma foto gera duas sugestões distintas e mantém o mesmo anexo',async()=>{
    const h=harness();h.context.photo=photo;
    const result=await h.run('readReceiptLotPhoto({files:[photo]})');
    eq(h.sent.length,1);eq(h.sent[0].url,'/api/purchases/lot-label-ocr');
    eq(result.file.content_base64,h.sent[0].body.evidence_file.content_base64);
    eq(result.dates.manufacture_date,'2024-01-02');eq(result.dates.physical_expiry_date,'2032-01-02');
  });
  testAsync('Compras: falha OCR preserva arquivo para preenchimento manual; PDF dispensa OCR',async()=>{
    const h=harness();h.context.photo=photo;
    h.context.api=async()=>{throw new Error('503');};
    const result=await h.run('readReceiptLotPhoto({files:[photo]})');eq(result.file.filename,'etiqueta.png');eq(result.error,'503');
    h.context.photo={name:'fabricante.pdf',type:'application/pdf',size:100};
    const pdf=await h.run('readReceiptLotPhoto({files:[photo]})');eq(pdf.file.filename,'fabricante.pdf');eq(pdf.error,undefined);
  });
  testAsync('Compras: sugestões não substituem correções manuais nem confirmam a prova',async()=>{
    const h=harness();const overlay=h.node('test');
    h.node('#receipt-capture-manufacture').value='2023-01-01';
    h.context.overlay=overlay;h.context.dates={manufacture_date:'2024-01-01',physical_expiry_date:'2032-01-01'};
    h.run('applyReceiptDateSuggestions(overlay,dates)');
    eq(h.node('#receipt-capture-manufacture').value,'2023-01-01');eq(h.node('#receipt-capture-expiry').value,'2032-01-01');
    eq(h.node('#receipt-capture-physical').checked,false);
  });
  testAsync('Compras: câmera preenche fabricação e validade; confirmação física permanece obrigatória',async()=>{
    const h=harness();const pending=h.run("openReceiptLotCaptureModal({},2,'Luva')");
    const input=h.node('#receipt-capture-file');input.files=[photo];
    await input.listeners.change({target:input});
    eq(h.node('#receipt-capture-manufacture').value,'2024-01-02');eq(h.node('#receipt-capture-expiry').value,'2032-01-02');
    assert(h.node('#receipt-capture-preview').src.startsWith('data:image/png;base64,'));
    h.node('#receipt-capture-lot').value='REAL';
    h.node('#receipt-capture-save').listeners.click();assert(h.node('#receipt-capture-error').textContent.includes('confirme'));
    h.node('#receipt-capture-physical').checked=true;h.node('#receipt-capture-save').listeners.click();
    const result=await pending;eq(result.manufacture_date,'2024-01-02');eq(result.manufacturer_validity_date,'2032-01-02');
    eq(result.evidence_file.filename,'etiqueta.png');eq(result.quantity,2);eq(result.capture_version,1);
  });
  testAsync('Compras: fabricação futura e validade anterior não encerram a captura',async()=>{
    const h=harness();h.context.initial=proof;const pending=h.run('openReceiptLotCaptureModal(initial,2)');
    h.node('#receipt-capture-lot').value='REAL';h.node('#receipt-capture-evidence').value='Etiqueta';h.node('#receipt-capture-physical').checked=true;
    h.node('#receipt-capture-manufacture').value='2099-01-01';h.node('#receipt-capture-save').listeners.click();
    assert(h.node('#receipt-capture-error').textContent.includes('fabricação'));
    h.node('#receipt-capture-manufacture').value='2024-01-01';h.node('#receipt-capture-expiry').value='2023-01-01';
    h.node('#receipt-capture-save').listeners.click();assert(!h.overlay.removed);
    h.node('#receipt-capture-cancel').listeners.click();eq(await pending,null);
  });
  testAsync('Compras: cancelar durante leitura impede aplicação da resposta atrasada',async()=>{
    const h=harness();let release;h.context.readReceiptLotPhoto=()=>new Promise(r=>{release=r;});
    const pending=h.run('openReceiptLotCaptureModal()');const input=h.node('#receipt-capture-file');input.files=[photo];
    const reading=input.listeners.change({target:input});h.node('#receipt-capture-cancel').listeners.click();
    eq(await pending,null);release({file:proof.evidence_file,dates:{manufacture_date:'2024-01-01'}});await reading;
    eq(h.node('#receipt-capture-manufacture').value,'');eq(h.context.openReceiptLotCaptureModal.busy,false);
  });
  testAsync('Compras: conferência envia captura uma vez por lote e não replica para outro item do mesmo EPI',async()=>{
    const h=harness();h.context.openReceiptLotCaptureModal=async()=>proof;
    h.context.items=[{id:1,epi_id:10,epi_name:'Luva',status:'received',effective_receive_quantity:2},
      {id:2,epi_id:10,epi_name:'Luva',status:'received',effective_receive_quantity:2}];
    const pending=h.run('openConferenciaModal(1,items)');
    await h.rows['1'].capture.listeners.click();h.node('#conferencia-confirm').listeners.click();
    const result=await pending;const a=result.received_items[0].lots[0],b=result.received_items[1].lots[0];
    eq(a.manufacture_date,'2024-01-02');eq(a.evidence_file.filename,'etiqueta.png');eq(a.quantity,2);
    eq(b.manufacturer_validity_date,'');eq(b.evidence_file,undefined);eq(b.manufacture_date,undefined);
    eq(h.sent.length,0);
  });
  testAsync('Compras: PO usa a mesma conferência e a quantidade recebida armazenada',async()=>{
    const h=harness();let modal;
    h.context._currentPoDetail={item:{id:5},items:[{id:1,quantity:99,quantity_received:2}]};
    h.context.openConferenciaModal=async(id,items,options)=>{modal={id,items,options};return{received_items:[{id:1,received:true,lots:[proof]}],comment:''};};
    await h.run("submitPoReceive('checked')");eq(modal.items[0].effective_receive_quantity,2);assert(modal.options.po);
    eq(h.sent.length,1);eq(h.sent[0].body.items[0].lots[0].manufacture_date,'2024-01-02');
    h.context.openConferenciaModal=async()=>null;await h.run("submitPoReceive('checked')");eq(h.sent.length,1);
  });
  testAsync('Compras: compatibilidade do leitor de validade nunca retorna fabricação',async()=>{
    const h=harness();h.context.photo=photo;eq(await h.run('readManufacturerValidityFromImage(photo)'),'2032-01-02');
    h.context.api=async()=>({manufacture_date:'2024-01-02',candidates:[]});eq(await h.run('readManufacturerValidityFromImage(photo)'),'');
  });
};
