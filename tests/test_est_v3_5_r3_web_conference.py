"""Exercise the production conference modal through its click handlers."""
import subprocess
from pathlib import Path


def test_web_conference_rejects_unchecked_invalid_line_and_preserves_partial_quantity():
    root = Path(__file__).resolve().parents[1]
    script = r'''
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync('static/app.js', 'utf8');
const start = source.indexOf('function openConferenciaModal(');
const end = source.indexOf('\nasync function updatePrStatus(', start);
const esc = String, CSS = {escape: String};
const tr = (key, fallback, params={}) => fallback.replace(/\{(\w+)\}/g, (_, k) => params[k]);
const bindAppListener = (element, event, callback) => { if(element) element[event] = callback; };
let current;
const document = { getElementById: () => null, body: {appendChild: () => {}}, createElement: () => {
 const rows = {}, elements = {};
 current = {style: {}, removed: false, remove(){this.removed=true},
 set innerHTML(html){ for(const match of html.matchAll(/data-conferencia-row="([^"]+)" data-eff-qty="([^"]+)"/g)) {
  const id = match[1]; rows[id] = {style:{}, getAttribute: () => match[2]};
  elements[id] = {value:id, checked:id==='1', closest: () => rows[id]};
 } },
 querySelector(selector){
  if(selector==='#conferencia-preview') return null;
  const row = selector.match(/^\[data-conferencia-row="([^"]+)"\]/); if(row) return rows[row[1]];
  const cb = selector.match(/^\[data-conferencia-item\]\[value="([^"]+)"\]/); if(cb) return elements[cb[1]];
  return elements[selector] ||= {style:{}, value:selector==='#conferencia-notes'?'Não recebido':'', textContent:''};
 }, querySelectorAll(selector){return selector==='[data-conferencia-item]' ? Object.values(elements).filter(e=>e.closest): []}
 }; return current;
} };
eval(source.slice(start, end));
(async () => {
 for(const qty of [0, null, -2, 'invalid', 1.5, true]) {
  const promise = openConferenciaModal(10, [{id:1,epi_name:'Válido',status:'received',effective_receive_quantity:2,quantity_requested:99},
   {id:2,epi_name:'Problemático',status:'not_received',effective_receive_quantity:qty,quantity_requested:99}]);
  const modal=current; modal.querySelector('#conferencia-confirm').click();
  assert.equal(modal.removed,false); const message=modal.querySelector('#conferencia-error').textContent;
  assert(message.includes('Linha 2') && message.includes('Problemático') && message.includes('#2'),message);
  modal.querySelector('#conferencia-cancel').click(); assert.equal(await promise,null);
 }
 const promise=openConferenciaModal(10,[{id:1,epi_name:'Parcial',status:'received',effective_receive_quantity:2,quantity_requested:99}]);
 current.querySelector('#conferencia-confirm').click(); const result=await promise;
 assert.equal(result.received_items[0].lots[0].quantity,2);
 assert.equal(result.received_items[0].received,true);
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', script], cwd=root, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
