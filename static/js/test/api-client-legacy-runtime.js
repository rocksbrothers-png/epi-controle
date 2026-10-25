'use strict';
// UBX-V3, Etapa 3 — contrato de `api` / `apiOptional` / `apiWithBootstrapRetry`
// depois da mudança do app.js para modules/api-client.js.
//
// Executa o api-client.js REAL num contexto isolado com um fetch falso e
// verifica o que sai (método, URL, headers, corpo, JWT) e o que volta
// (envelope { ok, data }, mensagens de erro por status, nonFatal, retry).
// É o mesmo pipeline que o app.js usava: os três nomes eram delegadores.
// As URLs são rotas reais do backend (tests/test_frontend_api_contract.py
// confere cada chamada de api do frontend contra as rotas do backend).
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');

function response(status, body, contentType = 'application/json') {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name) => (name.toLowerCase() === 'content-type' ? contentType : null) },
    text: async () => text,
    json: async () => JSON.parse(text)
  };
}

function load({ token = '', replies = [] } = {}) {
  const sent = [];
  const queue = [...replies];
  const ctx = vm.createContext({
    console: { warn() {}, error() {}, debug() {} },
    setTimeout: (fn) => fn(),
    Promise, JSON, Error, Object, Array, Number, String, Math,
    __EPI_APP_STATE__: { token },
    fetch: async (url, options) => {
      sent.push({ url, options });
      const next = queue.shift();
      if (next instanceof Error) { throw next; }
      return next || response(200, {});
    }
  });
  ctx.globalThis = ctx;
  vm.runInContext(fs.readFileSync(path.join(JS_ROOT, 'modules/api-client.js'), 'utf8'), ctx);
  return { ctx, sent };
}

async function rejects(promise) {
  try { await promise; } catch (error) { return error; }
  throw new Error('esperava rejeição');
}

module.exports = function ({ testAsync, test, assert, eq }) {
  test('UBX-V3 api-client: publica api/apiOptional/apiWithBootstrapRetry só em globalThis', () => {
    const { ctx } = load();
    for (const name of ['api', 'apiOptional', 'apiWithBootstrapRetry']) { eq(typeof ctx[name], 'function', name); }
    assert(!('api' in ctx.__EPI_API_CLIENT__), 'namespace do cliente não mudou');
    assert(!('api' in (ctx.__EPI_FRONTEND_HELPERS__ || {})), 'registro de helpers não mudou');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of ['api', 'apiOptional', 'apiWithBootstrapRetry']) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
  });

  testAsync('UBX-V3 api-client: api envia JWT e Content-Type; desembrulha { ok, data }', async () => {
    const { ctx, sent } = load({ token: 'jwt-123', replies: [response(200, { ok: true, data: { id: 9 } })] });
    const body = JSON.stringify({ a: 1 });
    const out = await ctx.api('/api/purchase-orders?unit_id=3', { method: 'POST', body });
    eq(JSON.stringify(out), '{"id":9}');
    eq(sent.length, 1);
    eq(sent[0].url, '/api/purchase-orders?unit_id=3');
    eq(sent[0].options.method, 'POST');
    eq(sent[0].options.body, body);
    eq(sent[0].options.headers.Authorization, 'Bearer jwt-123');
    eq(sent[0].options.headers['Content-Type'], 'application/json');
  });

  testAsync('UBX-V3 api-client: headers do chamador SUBSTITUEM os montados (peculiaridade preexistente)', async () => {
    // requestApiResponse faz fetch(path, { headers: buildApiHeaders(options), ...options }):
    // o spread de `options` sobrescreve `headers` — quem passa headers próprios
    // perde Authorization e Content-Type. Registrado em docs/UBX_APPJS_AUDITORIA.md
    // §11 como defeito preexistente; corrigir muda comportamento (fora da UBX-V3).
    const { ctx, sent } = load({ token: 'jwt-123' });
    await ctx.api('/api/units', { headers: { 'X-Extra': '1' } });
    eq(JSON.stringify(sent[0].options.headers), '{"X-Extra":"1"}');
    await ctx.api('/api/users', { headers: {} });
    eq(JSON.stringify(sent[1].options.headers), '{}', 'portal do colaborador passa headers vazios');
  });

  testAsync('UBX-V3 api-client: sem token não envia Authorization; payload sem envelope volta inteiro', async () => {
    const { ctx, sent } = load({ replies: [response(200, { items: [1, 2] })] });
    const out = await ctx.api('/api/units');
    eq(JSON.stringify(out), '{"items":[1,2]}');
    assert(!('Authorization' in sent[0].options.headers), 'sem Authorization');
  });

  testAsync('UBX-V3 api-client: mensagens de erro por status e nonFatal', async () => {
    const cases = [
      [401, {}, 'Usuário ou senha inválidos.', false],
      [403, { error: 'Sem permissão para esta unidade.' }, 'Sem permissão para esta unidade.', false],
      [404, {}, 'Rota da API não encontrada. Verifique versão do frontend/backend.', false],
      [503, { error: 'detalhe interno' }, 'Servidor temporariamente indisponível. Tente novamente em instantes.', true]
    ];
    for (const [status, body, message, nonFatal] of cases) {
      const { ctx } = load({ replies: [response(status, body)] });
      const error = await rejects(ctx.api('/api/users'));
      eq(error.message, message, `status ${status}`);
      eq(error.status, status);
      eq(Boolean(error.nonFatal), nonFatal, `nonFatal ${status}`);
    }
    const { ctx } = load({ replies: [response(200, { ok: false, error: { message: 'Recusado', code: 'X' } })] });
    const error = await rejects(ctx.api('/api/requests'));
    eq(error.message, 'Recusado');
    eq(error.code, 'X');
  });

  testAsync('UBX-V3 api-client: falha de rede vira mensagem amigável; resposta não JSON em /api é recusada', async () => {
    const offline = load({ replies: [new TypeError('Failed to fetch')] });
    eq((await rejects(offline.ctx.api('/api/employees'))).message, 'Falha de conexão com o servidor. Verifique sua internet e tente novamente.');
    const html = load({ replies: [response(200, '<html>login</html>', 'text/html')] });
    eq((await rejects(html.ctx.api('/api/feedbacks'))).code, 'INVALID_API_RESPONSE');
  });

  testAsync('UBX-V3 api-client: apiOptional devolve { ok, payload } ou { ok: false, error }', async () => {
    const good = load({ replies: [response(200, { v: 1 })] });
    eq(JSON.stringify(await good.ctx.apiOptional('/api/c')), '{"ok":true,"payload":{"v":1}}');
    const bad = load({ replies: [response(500, { error: 'quebrou' })] });
    const out = await bad.ctx.apiOptional('/api/d');
    eq(out.ok, false);
    eq(out.error.message, 'quebrou');
  });

  testAsync('UBX-V3 api-client: apiWithBootstrapRetry repete só em 502/503', async () => {
    const flaky = load({ replies: [response(503, {}), response(502, {}), response(200, { ok: true, data: 'pronto' })] });
    eq(await flaky.ctx.apiWithBootstrapRetry('/api/bootstrap', {}, { maxAttempts: 4, retryJitterMs: 0 }), 'pronto');
    eq(flaky.sent.length, 3);
    const hard = load({ replies: [response(400, { error: 'inválido' }), response(200, {})] });
    eq((await rejects(hard.ctx.apiWithBootstrapRetry('/api/e', {}, { maxAttempts: 4 }))).message, 'inválido');
    eq(hard.sent.length, 1, '400 não repete');
  });

  testAsync('UBX-V3 api-client: delegação resolvida na chamada (troca de apiFetch depois do boot vale)', async () => {
    const { ctx } = load();
    const calls = [];
    ctx.apiFetch = async (p, o) => { calls.push([p, o]); return 'trocado'; };
    const opts = { method: 'DELETE' };
    eq(await ctx.api('/api/stock/compliance', opts), 'trocado');
    assert(calls[0][1] === opts, 'mesmo objeto de opções repassado');
  });

  test('UBX-V3 views: o api local das views delega ao cliente único, sem fetch próprio', () => {
    for (const view of ['employee-portal', 'feedback', 'fichas', 'profile', 'purchases']) {
      const code = fs.readFileSync(path.join(JS_ROOT, 'views', `${view}.js`), 'utf8');
      assert(/function api\((path), (opts|options)\) \{\n\s+return globalThis\.api\(\1, \2\);\n\s+\}/.test(code), `${view}: api delega a globalThis.api`);
      assert(!/(^|[^\w$.])fetch\s*\(/m.test(code.replace(/\/\/.*$/gm, '')), `${view}: sem fetch cru`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const client = order.indexOf('/js/modules/api-client.js');
    for (const view of ['employee-portal', 'feedback', 'fichas', 'profile', 'purchases']) {
      assert(client >= 0 && client < order.indexOf(`/js/views/${view}.js`), `api-client antes de ${view}`);
    }
  });
};
