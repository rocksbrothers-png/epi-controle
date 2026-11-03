"""I18N-FULL-V1 — cobertura das mensagens de erro do backend por módulo.

O backend não muda: o cliente traduz na apresentação (`describeApiError` casa o
texto pt-BR recebido com `apiErrors.messages.*`). Este gate regenera o inventário
a partir do código (AST) e exige, para os módulos já concluídos:

1. toda mensagem não preservada ("traduzir" ou "já coberto") tem chave nos 5 catálogos, com os mesmos
   placeholders do texto pt-BR;
2. uma instância real da mensagem (valores sintéticos nos placeholders) resolve,
   no motor, para essa chave em todos os idiomas, sem alterar o payload;
3. mensagens preservadas por contrato (comparação textual no frontend) NÃO têm
   template — traduzi-las quebraria o ramo que depende do texto;
4. nenhuma tradução é cópia do pt-BR (en/es/fr/nb diferentes do texto de origem);
5. toda comparação textual sobre mensagem no frontend (`includes`/`startsWith`/...)
   está registrada em FRONTEND_TEXT_LOGIC do inventário — senão uma tradução
   futura poderia quebrar um ramo que ninguém declarou.

Uma mensagem nova num módulo concluído reprova o gate até ganhar tradução (ou
ser classificada como preservada no inventário, com motivo).
"""
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
# Módulos cujos lotes foram concluídos (cresce a cada lote).
DONE = ['purchases', 'ppe_tests', 'stock']


def _inventory():
    spec = importlib.util.spec_from_file_location('inv', ROOT / 'scripts/i18n/inventory_backend_errors.py')
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    return inv


_CACHE = {}


def _rows(module, tmp_dir):
    if module not in _CACHE:
        out = Path(tmp_dir) / f'i18n-inventory-{module}.json'
        subprocess.run(['python', str(ROOT / 'scripts/i18n/inventory_backend_errors.py'), '--modules', module,
                        '--json', str(out)], check=True, capture_output=True, cwd=ROOT)
        _CACHE[module] = json.loads(out.read_text(encoding='utf-8'))['items']
    return _inventory(), _CACHE[module]


def _missing(rows, cats):
    """Faltas de cobertura: chave ausente, placeholders divergentes ou cópia do pt-BR."""
    faltas = []
    for r in rows:
        # Depois de aplicada, a tradução aparece no inventário como "já coberto";
        # o gate vale para toda mensagem não preservada, nova ou já coberta.
        if r['decision'] == 'preservar':
            continue
        try:
            source = _leaf(cats['pt-BR'], r['catalog_entry'])
        except (KeyError, TypeError):
            faltas.append(f"pt-BR {r['catalog_entry']} ← {r['file']}:{r['line']} {r['template']!r}")
            continue
        pt_vars = sorted(set(re.findall(r'\{(\w+)\}', source)))
        for loc in LOCALES[1:]:
            try:
                value = _leaf(cats[loc], r['catalog_entry'])
            except (KeyError, TypeError):
                faltas.append(f"{loc} {r['catalog_entry']} ← {r['file']}:{r['line']} {r['template']!r}")
                continue
            if sorted(set(re.findall(r'\{(\w+)\}', value))) != pt_vars:
                faltas.append(f'{loc} {r["catalog_entry"]}: placeholders divergentes')
            if value == source:
                faltas.append(f'{loc} {r["catalog_entry"]}: cópia do pt-BR')
    return faltas


def _catalogs():
    return {loc: json.loads((ROOT / 'static/i18n' / f'{loc}.json').read_text(encoding='utf-8')) for loc in LOCALES}


def _leaf(data, key):
    for part in key.split('.'):
        data = data[part]
    return data


@pytest.mark.parametrize('module', DONE)
def test_toda_mensagem_traduzivel_tem_chave_nos_5_idiomas(module, tmp_path_factory):
    _inv, rows = _rows(module, tmp_path_factory.mktemp('inv'))
    assert any(r['decision'] != 'preservar' for r in rows), 'inventário vazio: o gate não estaria verificando nada'
    faltas = _missing(rows, _catalogs())
    assert not faltas, 'mensagens sem tradução:\n' + '\n'.join(faltas[:40])


@pytest.mark.parametrize('module', DONE)
def test_instancia_real_resolve_para_a_chave_e_preserva_payload(module, tmp_path_factory):
    _inv, rows = _rows(module, tmp_path_factory.mktemp('inv'))
    cases, preserved = [], []
    for r in rows:
        sample = re.sub(r'\{(\w+)\}', lambda m: f'X{m.group(1)}7', r['template'])
        if r['decision'] != 'preservar':
            cases.append({'source': sample, 'key': r['catalog_entry']})
        elif r['decision'] == 'preservar':
            preserved.append(sample)
    script = r'''
const fs=require('fs'),path=require('path'),vm=require('vm');
const root=process.argv[1],cases=JSON.parse(process.argv[2]),preserved=JSON.parse(process.argv[3]);
const dict={};for(const l of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'])dict[l]=JSON.parse(fs.readFileSync(path.join(root,'static/i18n',l+'.json'),'utf8'));
const ctx={console,Intl,Promise,Symbol,JSON,Object,Array,String,Number,RegExp,Error,Map,WeakMap,Set,Math,
 document:{documentElement:{lang:''},querySelectorAll:()=>[],createDocumentFragment:()=>({appendChild(){}})},
 navigator:{language:'pt-BR'},CustomEvent:function(){},addEventListener(){},dispatchEvent(){},
 fetch:async(u)=>{const l=decodeURIComponent(String(u).split('/').pop());return{ok:true,json:async()=>({locale:l,fallback:false,translations:dict[l]})};}};
ctx.window=ctx;ctx.globalThis=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'static/i18n.js'),'utf8'),ctx);
(async()=>{const errs=[];
 for(const l of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']){await ctx.EpiI18n.setLang(l,{persist:false,translate:false});
  for(const c of cases)for(const extra of [{code:'X_CODE'},{}]){const payload={error:c.source,...extra};const before=JSON.stringify(payload);
   const r=ctx.EpiI18n.describeApiError(payload);
   if(r.key!==c.key)errs.push(l+' '+c.key+' <- '+c.source+' => '+r.key);
   if(JSON.stringify(payload)!==before)errs.push('payload alterado '+c.key);
   if(/\{\w+\}/.test(r.text))errs.push('placeholder sobrou '+c.key);}
  for(const s of preserved){const r=ctx.EpiI18n.describeApiError({error:s});
   if(r.key)errs.push('preservada ganhou tradução: '+s+' => '+r.key);}}
 if(errs.length){console.error(errs.slice(0,40).join('\n'));process.exit(1);}})();
'''
    result = subprocess.run(['node', '-e', script, str(ROOT), json.dumps(cases), json.dumps(preserved)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-4000:]


def test_detector_acusa_falta_copia_e_placeholder():
    """Prova do gate com linhas sintéticas: cada defeito aparece como falta."""
    cats = _catalogs()
    real = next(k for k in cats['pt-BR']['apiErrors']['messages'] if '{' in cats['pt-BR']['apiErrors']['messages'][k])
    rows = [{'decision': 'traduzir', 'catalog_entry': 'apiErrors.messages.m_inexistente', 'file': 'x.py', 'line': 1,
             'template': 'Mensagem nova.'},
            {'decision': 'já coberto', 'catalog_entry': f'apiErrors.messages.{real}', 'file': 'x.py', 'line': 2,
             'template': cats['pt-BR']['apiErrors']['messages'][real]}]
    assert any('m_inexistente' in f for f in _missing(rows, cats))
    copia = json.loads(json.dumps(cats))
    copia['en-GB']['apiErrors']['messages'][real] = cats['pt-BR']['apiErrors']['messages'][real]
    assert any('cópia do pt-BR' in f for f in _missing(rows[1:], copia))
    copia['fr-FR']['apiErrors']['messages'][real] = 'Texte sans variable.'
    assert any('placeholders divergentes' in f for f in _missing(rows[1:], copia))


COMPARISON = re.compile(r"""(?:message|msg|Message|error|reason)\w*(?:\(\))?(?:\?\.)?\s*\.?(?:toLowerCase\(\)\s*\.)?"""
                        r"""(?:includes|startsWith|endsWith|indexOf)\(\s*['"]([^'"]+)['"]""")


def test_toda_comparacao_textual_do_frontend_esta_declarada():
    """Uma comparação com o texto do erro no frontend precisa estar em FRONTEND_TEXT_LOGIC:
    assim a mensagem que a alimenta é preservada e não ganha tradução por engano."""
    needles = _inventory().FRONTEND_TEXT_LOGIC_NEEDLES
    achados = []
    for path in sorted((ROOT / 'static').rglob('*.js')):
        if '/test/' in str(path) or path.name == 'i18n.js':
            continue
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            for needle in COMPARISON.findall(line):
                if re.search(r'[A-Za-zÀ-ÿ0-9]', needle) and needle.lower() not in needles:
                    achados.append(f'{path.relative_to(ROOT)}:{number}: {needle!r}')
    assert not achados, 'comparação textual não declarada em FRONTEND_TEXT_LOGIC:\n' + '\n'.join(achados)


def test_scanner_de_comparacao_pega_o_padrao():
    assert COMPARISON.findall("if (loweredMessage.includes('não encontrado')) {") == ['não encontrado']
    assert COMPARISON.findall("msg.toLowerCase().includes('bloqueado')") == ['bloqueado']
    assert COMPARISON.findall("if (error?.message?.startsWith('Prazo')) {") == ['Prazo']
