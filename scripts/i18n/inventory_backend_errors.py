"""Inventário das mensagens de erro do backend por módulo (I18N-FULL-V1).

O campo com a chave do catálogo chama-se `catalog_entry` (e não `key`): o gitleaks
(generic-api-key) trata `"key": "<valor com hash>"` como credencial — foi a origem
das 94 exceções históricas da I18N.

Lê o código Python (AST), sem importar nem executar nada, e lista cada mensagem
de erro exposta ao cliente com: arquivo/linha/função, tipo de saída, status HTTP,
formato do payload, endpoint(s) prováveis, testes Python que citam o texto,
comparações textuais no frontend, chave existente/proposta e a decisão
(traduzir na apresentação ou preservar por contrato).

O backend NÃO é alterado: a tradução acontece no cliente, por `describeApiError`
(static/i18n.js), que casa o texto pt-BR recebido com `apiErrors.messages.*`.
Status, `code`, payload e o texto original continuam idênticos no fio.

Uso:
  python scripts/i18n/inventory_backend_errors.py --modules purchases ppe_tests stock \
      --json docs/i18n/I18N-FULL-V1/backend-errors-inventory.json
"""
import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PT = re.compile(r'[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]|\b(não|de|para|sem|inválid|obrigatóri|encontrad|deve|permitid|informe|selecione)', re.IGNORECASE)
STATUS_BY_EXCEPTION = {
    'ValueError': 400, 'PermissionError': 403, 'LookupError': 404, 'KeyError': 404,
    'RuntimeError': 500, 'TypeError': 400,
}
# Comparações textuais do frontend que decidem comportamento (inventário manual, conferido por grep):
# a mensagem que as alimenta precisa continuar idêntica para o ramo continuar funcionando.
FRONTEND_TEXT_LOGIC = [
    {'endpoint': '/api/stock/lookup-qr', 'needle': 'não encontrado',
     'where': 'static/app.js handleDeliveryQrScan: loweredMessage.includes("não encontrado")'},
    {'endpoint': '/api/stock/labels/reprint', 'needle': 'temporariamente indisponível',
     'where': 'static/app.js reprintStockLabelByQr: loweredMessage.includes("temporariamente indisponível")'},
    {'endpoint': '/api/stock/labels/reprint', 'needle': 'service unavailable',
     'where': 'static/app.js reprintStockLabelByQr: loweredMessage.includes("service unavailable")'},
    {'endpoint': '/api/stock/labels/reprint', 'needle': '503',
     'where': 'static/app.js reprintStockLabelByQr: loweredMessage.includes("503")'},
    {'endpoint': '/api/employee-access', 'needle': 'bloqueado',
     'where': 'static/js/views/employee-portal.js: msg.includes("bloqueado")'},
    {'endpoint': '/api/employee-access', 'needle': 'novo link',
     'where': 'static/js/views/employee-portal.js: msg.includes("novo link")'},
]
# O gate confere que toda comparação textual sobre mensagem no frontend está nesta lista.
FRONTEND_TEXT_LOGIC_NEEDLES = {f['needle'] for f in FRONTEND_TEXT_LOGIC}


# Prefixos montados no backend com formato fixo e uma única origem (conferido no código):
# o template os expande para que a frase inteira seja traduzida, sem mudar o backend.
EXPANSIONS = {
    'purchases': [
        ('{label}: ', 'Linha {line} da cotação: '),   # service.py: label = f'Linha {n} da cotação'
        ('{entry}: ', 'Linha {line} da cotação: '),   # service.py: entry["label"] (mesma origem)
    ],
}


def shape(text):
    return re.sub(r'\{\w+\}', '{}', text)


# Exceções que embrulham a mensagem num prefixo fixo. O wrapper vai para
# apiErrors.wrappers (o motor traduz {cause} recursivamente) e a mensagem interna
# é inventariada como mensagem própria.
WRAPPERS = {
    'ReceiptValidationError': {  # modules/purchases/service.py: f"Linha {index} — {item_name} (item #{item_id}): {message}"
        'message_index': 2, 'template': 'Linha {line} — {item} (item #{itemid}): {cause}', 'status': 400,
        'payload': "{'ok': False, 'error': <mensagem>, 'validation': {code, line_index, item_id, item_name, field}}",
    },
    'RollbackConflict': {  # modules/data_migration/rollback.py: f'Reversão recusada: {reason}. Nenhum registro foi revertido.'
        'message_index': 0, 'template': 'Reversão recusada: {cause}. Nenhum registro foi revertido.', 'status': 400,
        'payload': "{'error': <mensagem>}", 'vars': ['cause'],
    },
    'SourceError': {  # modules/data_migration/sources.py: f'{message} (linha {row}).'
        'message_index': 0, 'template': '{cause} (linha {line}).', 'status': 400,
        'payload': "{'error': <mensagem>, 'diagnostics': [...]}", 'vars': ['cause', 'line'],
    },
}


def key_for(text):
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    return ('apiErrors.wrappers.w_' if '{cause}' in text else 'apiErrors.messages.m_') + digest


def flatten(node, prefix=''):
    out = {}
    for k, v in (node or {}).items():
        if isinstance(v, dict):
            out.update(flatten(v, f'{prefix}{k}.'))
        else:
            out[f'{prefix}{k}'] = v
    return out


def var_name(expr, used):
    """Nome estável para o placeholder: último identificador da expressão."""
    names = [n.id if isinstance(n, ast.Name) else n.attr for n in ast.walk(expr) if isinstance(n, (ast.Name, ast.Attribute))]
    base = re.sub(r'[^a-z0-9]', '', (names[0] if names else 'value').lower()) or 'value'
    name, i = base, 2
    while name in used:
        name, i = f'{base}{i}', i + 1
    used.add(name)
    return name


def template_of(node, used=None):
    used = set() if used is None else used
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # 'Texto fixo: ' + valor  →  'Texto fixo: {valor}'
        parts, names = [], []
        for side in (node.left, node.right):
            text, side_names = template_of(side, used)
            if text is None:
                name = var_name(side, used)
                text, side_names = '{' + name + '}', [name]
            parts.append(text)
            names += side_names
        joined = ''.join(parts)
        return (joined, names) if re.sub(r'\{\w+\}', '', joined).strip() else (None, [])
    if isinstance(node, ast.JoinedStr):
        parts, names = [], []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                n = var_name(v.value, used)
                names.append(n)
                parts.append('{' + n + '}')
        return ''.join(parts), names
    return None, []


def find_forwarders(sources):
    """Funções que levantam a exceção com o próprio parâmetro como mensagem
    (ex.: _finite_money(value, message) → raise ValueError(message))."""
    out = {}
    for path in sources:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = [a.arg for a in fn.args.args]
            for node in ast.walk(fn):
                if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args \
                        and isinstance(node.exc.args[0], ast.Name) and node.exc.args[0].id in params:
                    exc = node.exc.func.id if isinstance(node.exc.func, ast.Name) else getattr(node.exc.func, 'attr', '?')
                    out[fn.name] = (params.index(node.exc.args[0].id), node.exc.args[0].id, exc)
    return out


class Collector(ast.NodeVisitor):
    def __init__(self, path, source, forwarders=None):
        self.path, self.source, self.stack, self.items = path, source, [], []
        self.forwarders = forwarders or {}

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def add(self, node, text, names, kind, status, payload):
        if not text or (not PT.search(text) and not kind.startswith('wrapper ')):
            return
        self.items.append({'file': str(self.path.relative_to(ROOT)), 'line': node.lineno,
                           'function': self.stack[-1] if self.stack else '<module>', 'kind': kind,
                           'http_status': status, 'payload': payload, 'template': text, 'vars': names})

    def visit_Raise(self, node):
        exc = node.exc
        if isinstance(exc, ast.Call) and exc.args:
            name = exc.func.id if isinstance(exc.func, ast.Name) else getattr(exc.func, 'attr', '?')
            if name in WRAPPERS:
                w = WRAPPERS[name]
                self.add(node, w['template'], w.get('vars', ['line', 'item', 'itemid', 'cause']), f'wrapper {name}',
                         w['status'], w['payload'])
                if len(exc.args) > w['message_index']:
                    text, names = template_of(exc.args[w['message_index']])
                    self.add(node, text, names, f'causa de {name}', w['status'], w['payload'])
                self.generic_visit(node)
                return
            text, names = template_of(exc.args[0])
            status = STATUS_BY_EXCEPTION.get(name)
            payload = "{'error': <mensagem>}" if status in (400, 403) else 'tratado pela rota'
            self.add(node, text, names, f'raise {name}', status or 'depende da rota', payload)
        self.generic_visit(node)

    def visit_Call(self, node):
        fn = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
        if fn in self.forwarders:
            index, param, exc = self.forwarders[fn]
            arg = node.args[index] if len(node.args) > index else next(
                (k.value for k in node.keywords if k.arg == param), None)
            if arg is not None:
                text, names = template_of(arg)
                status = STATUS_BY_EXCEPTION.get(exc, 'depende da rota')
                self.add(node, text, names, f'via {fn}() → raise {exc}', status, "{'error': <mensagem>}")
        if fn == 'send_json' and len(node.args) >= 3 and isinstance(node.args[2], ast.Dict):
            status = node.args[1].value if isinstance(node.args[1], ast.Constant) else '?'
            self._dict(node.args[2], node, f'send_json {status}', status)
        elif fn in ('bad_request', 'forbidden', 'unauthorized') and len(node.args) >= 2:
            text, names = template_of(node.args[1])
            self.add(node, text, names, fn, {'bad_request': 400, 'forbidden': 403, 'unauthorized': 401}[fn], "{'error': <mensagem>}")
        self.generic_visit(node)

    def visit_Return(self, node):
        if isinstance(node.value, ast.Dict):
            self._dict(node.value, node, 'return dict', 'depende da rota')
        self.generic_visit(node)

    def _dict(self, d, node, kind, status):
        for k, v in zip(d.keys, d.values):
            if not (isinstance(k, ast.Constant) and k.value == 'error'):
                continue
            if isinstance(v, ast.Dict):
                code, msg = None, None
                for k2, v2 in zip(v.keys, v.values):
                    if isinstance(k2, ast.Constant) and k2.value == 'code' and isinstance(v2, ast.Constant):
                        code = v2.value
                    if isinstance(k2, ast.Constant) and k2.value == 'message':
                        msg = v2
                if msg is not None:
                    text, names = template_of(msg)
                    self.add(node, text, names, kind, status, f"{{'ok': False, 'error': {{'code': {code!r}, 'message': <mensagem>}}}}")
            else:
                text, names = template_of(v)
                self.add(node, text, names, kind, status, "{'error': <mensagem>}")


class LiteralDomains:
    """Valores possíveis de um parâmetro quando TODAS as chamadas passam literais
    (ou usam o default literal). Ex.: acao='editar estoque mínimo' em stock/routes.py,
    physical_date(..., 'Validade física'). Se uma chamada passar valor dinâmico, o
    domínio é desconhecido e o template não é expandido."""

    def __init__(self, sources):
        self.defs, self.calls = {}, {}
        for path in sources:
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = node.args
                    params = [a.arg for a in args.args] + [a.arg for a in args.kwonlyargs]
                    defaults = dict(zip([a.arg for a in args.args][len(args.args) - len(args.defaults):], args.defaults))
                    defaults.update({a.arg: d for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is not None})
                    self.defs.setdefault(node.name, (params, defaults))
                elif isinstance(node, ast.Call):
                    callee = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', None)
                    if callee:
                        self.calls.setdefault(callee, []).append(node)

    def domain(self, function, param):
        if function not in self.defs or param not in self.defs[function][0]:
            return None
        params, defaults = self.defs[function]
        index, values = params.index(param), set()
        for call in self.calls.get(function, []):
            arg = next((k.value for k in call.keywords if k.arg == param), None)
            if arg is None and len(call.args) > index:
                arg = call.args[index]
            if arg is None:
                arg = defaults.get(param)
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                return None
            values.add(arg.value)
        return sorted(values) or None


# Nomes que coincidem com métodos de dict/list/str/conexão: no grafo global, por nome,
# qualquer `payload.get(...)` pareceria chamar uma função `get` de serviço.
GENERIC_METHOD_NAMES = {'get', 'set', 'update', 'pop', 'items', 'keys', 'values', 'append', 'add', 'remove',
                        'format', 'strip', 'split', 'join', 'execute', 'fetchone', 'fetchall', 'commit', 'rollback',
                        'close', 'run', 'copy', 'clear', 'count', 'index', 'insert', 'extend', 'sort', 'replace',
                        'encode', 'decode', 'lower', 'upper', 'read', 'write', 'send', 'load', 'dump', 'parse'}


class CallGraph:
    """Rotas registradas (router.register) e quem chama quem, por nome, em modules/**."""

    def __init__(self):
        self.routes, self.callers, self.local_callers = {}, {}, {}
        sources = sorted((ROOT / 'modules').rglob('*.py')) + sorted((ROOT / 'epi_backend').rglob('*.py'))
        sources += [ROOT / name for name in ('app.py', 'server_postgres.py') if (ROOT / name).exists()]
        for path in sources:
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'register' and len(node.args) >= 3:
                    method, route, handler = node.args[:3]
                    if isinstance(method, ast.Constant) and isinstance(route, ast.Constant):
                        name = handler.id if isinstance(handler, ast.Name) else getattr(handler, 'attr', None)
                        if name:
                            pretty = re.sub(r'^\^|\$$', '', route.value).replace(r'(\d+)', '<id>').replace('\\', '')
                            self.routes.setdefault(name, set()).add(f'{method.value} {pretty}')
                # Handler criado por fábrica: handle_x = _make_action(service_fn, ...)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.args:
                    target = node.targets[0]
                    first = node.value.args[0]
                    if isinstance(target, ast.Name) and isinstance(first, (ast.Name, ast.Attribute)):
                        fn = first.id if isinstance(first, ast.Name) else first.attr
                        self.callers.setdefault(fn, set()).add(target.id)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for call in ast.walk(node):
                        if isinstance(call, ast.Call):
                            callee = call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, 'attr', None)
                            if callee and callee != node.name:
                                self.callers.setdefault(callee, set()).add(node.name)
                                self.local_callers.setdefault((self._package(path), callee), set()).add(node.name)

    @staticmethod
    def _package(path):
        parts = Path(path).resolve().relative_to(ROOT).parts
        return parts[1] if len(parts) > 2 and parts[0] == 'modules' else parts[0]

    def endpoints(self, function, depth=5, package=None):
        """Busca primeiro chamadores no próprio pacote (nomes genéricos como `get` ou
        `_authorize` existem em vários módulos); só sem resultado local usa o grafo global."""
        if package:
            local = self._walk(function, depth, lambda fn: self.local_callers.get((package, fn), ()))
            if local:
                return local
        if function in GENERIC_METHOD_NAMES:
            return []  # `x.get(...)` em todo o código não é chamada desta função
        return self._walk(function, depth,
                          lambda fn: () if fn in GENERIC_METHOD_NAMES else self.callers.get(fn, ()))

    def _walk(self, function, depth, callers_of):
        seen, frontier, found = {function}, [function], set()
        for _ in range(depth):
            nxt = []
            for fn in frontier:
                found |= self.routes.get(fn, set())
                for caller in callers_of(fn):
                    if caller not in seen:
                        seen.add(caller)
                        nxt.append(caller)
            frontier = nxt
        return sorted(found)


def python_tests_citing(text, tests_src):
    fixed = max(re.split(r'\{\w+\}', text), key=len).strip()
    if len(fixed) < 14:
        return []
    return sorted({name for name, src in tests_src.items() if fixed in src})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--modules', nargs='+', required=True)
    ap.add_argument('--json', type=Path)
    args = ap.parse_args()
    catalog = json.loads((ROOT / 'static/i18n/pt-BR.json').read_text(encoding='utf-8'))
    existing = {shape(v): 'apiErrors.' + k for k, v in flatten(catalog['apiErrors']).items()}
    other = {shape(v): k for k, v in flatten(catalog).items() if not k.startswith('apiErrors.')
             and re.search(r'error|invalid|failed|denied|notfound|required|mismatch|unavailable|forbidden', k, re.IGNORECASE)}
    tests_src = {p.name: p.read_text(encoding='utf-8', errors='ignore') for p in (ROOT / 'tests').glob('test_*.py')}
    graph = CallGraph()
    every_source = sorted((ROOT / 'modules').rglob('*.py'))
    forwarders = find_forwarders(every_source)
    domains = LiteralDomains(every_source)
    rows, shapes_seen = [], {}
    for module in args.modules:
        mdir = ROOT / 'modules' / module
        for path in sorted(mdir.glob('*.py')):
            src = path.read_text(encoding='utf-8')
            c = Collector(path, src, forwarders)
            c.visit(ast.parse(src))
            expanded = []
            for item in c.items:
                expanded.append(item)
                for var in item['vars']:
                    values = domains.domain(item['function'], var)
                    if values:
                        for value in values:
                            expanded.append(dict(item, template=item['template'].replace('{' + var + '}', value),
                                                 vars=[v for v in item['vars'] if v != var],
                                                 literal_domain=f'{var}={value!r} (todas as chamadas de {item["function"]}() passam literais)'))
            for item in expanded:
                for old, new in EXPANSIONS.get(module, []):
                    if item['template'].startswith(old):
                        item['template'] = new + item['template'][len(old):]
                        item['vars'] = ['line'] + [v for v in item['vars'] if v not in ('label', 'entry')]
                        item['expanded_prefix'] = f'{old.strip()} → {new.strip()}'
                text = item['template']
                eps = graph.endpoints(item['function'], package=module)
                # Proteção de contrato usa o grafo global (superconjunto, conservador).
                eps_all = sorted(set(eps) | set(graph.endpoints(item['function'])))
                fixed = re.sub(r'\{\w+\}', '', text)
                logic = [f['where'] for f in FRONTEND_TEXT_LOGIC
                         if f['needle'] in text.lower() and any(f['endpoint'] in e for e in eps_all)]
                # Contrato primeiro: uma mensagem que alimenta comparação textual continua
                # "preservar" mesmo que alguém crie um template para ela (o gate então reprova).
                if logic:
                    decision, reason, key = 'preservar', 'comparação textual no frontend decide comportamento', None
                elif shape(text) in existing:
                    decision, reason, key = 'já coberto', 'template existente', existing[shape(text)]
                elif shape(text) in other:
                    decision, reason, key = 'já coberto', 'chave de UI casada pelo motor', other[shape(text)]
                elif shape(text) in shapes_seen:
                    decision, reason, key = 'traduzir', 'mesma forma de outra mensagem: reutiliza a chave', shapes_seen[shape(text)]
                elif not fixed.strip() or re.fullmatch(r'\{\w+\}', text.strip()):
                    decision, reason, key = 'preservar', 'mensagem é só um valor dinâmico (opaco)', None
                elif item['vars'] and len(fixed) < 8:
                    decision, reason, key = 'preservar', 'texto fixo < 8 caracteres: o motor recusa por segurança', None
                elif re.search(r'\{\w+\}\{\w+\}', text):
                    decision, reason, key = 'preservar', 'variáveis adjacentes: correspondência ambígua', None
                else:
                    decision, reason, key = 'traduzir', 'apresentação no cliente; contrato intacto', key_for(text)
                    shapes_seen[shape(text)] = key
                rows.append(dict(item, module=module, endpoints=eps, python_tests=python_tests_citing(text, tests_src),
                                 frontend_text_logic=logic, consumers='api-client.createApiError → describeApiError'
                                 + ('; ' + '; '.join(logic) if logic else ''), decision=decision, reason=reason, catalog_entry=key,
                                 locales=['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'],
                                 fallback='sem tradução no idioma → pt-BR do catálogo; sem template → texto original do servidor'))
    uniq = {}
    for r in rows:
        uniq.setdefault((r['module'], r['template']), r)
    summary = {}
    for (module, _), r in uniq.items():
        s = summary.setdefault(module, {'ocorrencias': 0, 'unicas': 0, 'traduzir': 0, 'já coberto': 0, 'preservar': 0})
        s['unicas'] += 1
        s[r['decision']] += 1
    for r in rows:
        summary[r['module']]['ocorrencias'] += 1
    out = {'summary': summary, 'items': rows}
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == '__main__':
    main()
