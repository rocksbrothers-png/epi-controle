'use strict';
// UBX-V4, Etapa C — verificação de RBAC da interface antes × depois.
//
// As regras can* saíram do app.js para modules/auth/business/access-rules.js
// (puras) com o adaptador modules/auth/ui/access-context.js. Este teste roda
// as funções ORIGINAIS (fatiadas do app.js do commit da Etapa B2, dentro de um
// bloco com os mapas VIEW_* e CONFIGURATION_ADMIN_ROLES do próprio app.js) e
// as NOVAS (módulos + o adaptador canAccessView do app.js atual) sobre a MESMA
// matriz e exige decisão idêntica em cada célula:
// - atores: os 9 perfis + perfil desconhecido + sem usuário;
// - permissões: lista do perfil, lista vazia (cai no fallback real de
//   ROLE_PERMISSIONS via normalizePermissions de modules/auth.js), só
//   permissões de leitura e uma lista arbitrária com espaços;
// - alvos (gestão de usuários): todos os perfis, mesma empresa / outra / sem
//   empresa, e o próprio ator;
// - views (canAccessView): todas as do VIEW_PERMISSIONS do app.js + extras,
//   com visibilidade de módulos ausente, vazia, ligada, desligada e com a
//   alternativa de Terceirizados.
// Regras de interface: o backend continua decidindo cada requisição.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const APP = path.resolve(JS_ROOT, '..', 'app.js');
const TARGET_RULES = ['sameCompany', 'canManageUser', 'canDeleteUser', 'canPromoteToAdmin', 'canPromoteToGeneralAdmin', 'canDemoteAdmin',
  'canDemoteGeneralAdmin', 'canToggleActive', 'canGenerateRecoveryToken'];
const AREA_RULES = ['canManageUsers', 'canManageEpi', 'canViewReports', 'canAccessCommercialArea', 'canConfigureMyCompany',
  'canPrintPurchaseQrLabels', 'canManagePurchaseFunctions'];
const ROLES = ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee', 'certification_readonly', 'auditor_x'];
const CONST_NAMES = ['VIEW_PERMISSIONS', 'VIEW_MODULE', 'VIEW_MODULE_ALTERNATIVES', 'VIEW_PERMISSION_ALTERNATIVES', 'CONFIGURATION_ADMIN_ROLES'];

function sliceTopLevel(lines, startsWith) {
  const s = lines.findIndex((l) => l.startsWith(startsWith));
  if (s < 0) { throw new Error(`não achei ${startsWith}`); }
  if (lines[s].trimEnd().endsWith(';')) { return lines[s]; }
  let e = s;
  while (!/^}/.test(lines[e])) { e++; }
  return lines.slice(s, e + 1).join('\n');
}

function baseContext(state) {
  const ctx = vm.createContext({ Object, Array, String, Boolean, Set, JSON, __EPI_APP_STATE__: state });
  ctx.globalThis = ctx;
  for (const rel of ['core/constants.js', 'core/permissions.js', 'modules/auth.js']) {
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), ctx);
  }
  return ctx;
}

// Funções originais: como no app.js (bloco com state e as constantes).
function loadOriginal(state, appSource) {
  const ctx = baseContext(state);
  const lines = appSource.split('\n');
  const names = ['normalizePermissionList', 'hasPermission', 'hasConfigurationAccess', ...TARGET_RULES, ...AREA_RULES, 'canAccessView'];
  const consts = CONST_NAMES.map((n) => sliceTopLevel(lines, `const ${n} = `));
  const fns = names.map((n) => sliceTopLevel(lines, `function ${n}(`));
  vm.runInContext(`{ const state = globalThis.__EPI_APP_STATE__;\n${consts.join('\n')}\n${fns.join('\n')}\n`
    + `${names.map((n) => `globalThis.${n} = ${n};`).join(' ')} }`, ctx);
  return ctx;
}

// Versão nova: módulos + o adaptador canAccessView do app.js atual.
function loadCurrent(state, appSource) {
  const ctx = baseContext(state);
  for (const rel of ['modules/auth/business/access-rules.js', 'modules/auth/ui/access-context.js']) {
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), ctx);
  }
  const lines = appSource.split('\n');
  const consts = CONST_NAMES.map((n) => sliceTopLevel(lines, `const ${n} = `));
  vm.runInContext(`{ const state = globalThis.__EPI_APP_STATE__;\n${consts.join('\n')}\n${sliceTopLevel(lines, 'function canAccessView(')}\n`
    + 'globalThis.canAccessView = canAccessView; }', ctx);
  return ctx;
}

function permissionSets(ctx, role, viewPerms) {
  const own = (ctx.ROLE_PERMISSIONS[role] || []).slice();
  return {
    perfil: own,
    vazia: [],
    leitura: own.filter((p) => p.endsWith(':view')),
    arbitraria: ['users:update', 'settings:view', 'commercial:view', 'stock:view', 'unit_links:manage', 'employees:create_simplified'],
    // todas as permissões existentes (perfis + as exigidas pelas views, algumas
    // só chegam do backend, ex. employees:transfer): leva cada perfil até as
    // restrições de papel
    todas: [...new Set([...Object.values(ctx.ROLE_PERMISSIONS).flat(), ...viewPerms])]
  };
}

function views(appSource) {
  const lines = appSource.split('\n');
  const block = sliceTopLevel(lines, 'const VIEW_PERMISSIONS = ');
  const keys = [...block.matchAll(/^\s+'?([\w-]+)'?\s*:/gm)].map((m) => m[1]);
  return [...new Set([...keys, 'configuracao', 'gestao-colaborador', 'terceirizados', 'view-inexistente', ''])];
}

const VISIBILITY = {
  ausente: undefined,
  vazia: {},
  ligada: { terceirizados: true, terceirizados_colaboradores: true, estoque: true, entregas: true, fichas: true, compras: true },
  desligada: { terceirizados: false, terceirizados_colaboradores: false, estoque: false, entregas: false, fichas: false, compras: false, relatorios: false },
  alternativa: { terceirizados: false, terceirizados_colaboradores: true },
  alternativaDesligada: { terceirizados: false, terceirizados_colaboradores: 0 },
  // valores "falsos" que não são false: a regra testa veracidade, não === false
  falsosNaoBooleanos: { estoque: 0, entregas: null, fichas: '', compras: undefined, relatorios: 'sim', terceirizados: 0, terceirizados_colaboradores: 'x' }
};

function decisions(loader, appSource, permsAppSource) {
  const out = [];
  const probe = baseContext({ permissions: [], user: null });
  const actors = [...ROLES.map((role) => ({ id: 7, role, company_id: 901 })), null];
  const targets = [];
  for (const role of ROLES.slice(0, 9)) {
    for (const company of [901, 902, null]) { targets.push({ id: 50, role, company_id: company }); }
  }
  targets.push({ id: 7, role: 'master_admin', company_id: 901 }, { id: '7', role: 'admin', company_id: '901' }, { id: 7, role: 'general_admin', company_id: 901 });
  const viewList = views(permsAppSource);
  const permLines = permsAppSource.split('\n');
  const viewPerms = ['VIEW_PERMISSIONS', 'VIEW_PERMISSION_ALTERNATIVES']
    .flatMap((n) => [...sliceTopLevel(permLines, `const ${n} = `).matchAll(/:\s*'([^']+)'/g)].flatMap((m) => m[1].split(/\s+/)));
  for (const actor of actors) {
    const sets = permissionSets(probe, actor ? actor.role : 'none', viewPerms);
    for (const [setName, permissions] of Object.entries(sets)) {
      for (const [visName, visibility] of Object.entries(VISIBILITY)) {
        const state = { user: actor, permissions: permissions.slice(), moduleVisibility: visibility };
        const ctx = loader(state, appSource);
        const key = `${actor ? actor.role : 'sem-usuario'}/${setName}/${visName}`;
        if (visName === 'ausente') {
          for (const t of targets) {
            for (const rule of TARGET_RULES) { out.push([key, rule, `${t.role}:${t.company_id}:${t.id}`, ctx[rule](t)]); }
          }
          for (const rule of AREA_RULES) { out.push([key, rule, '', ctx[rule]()]); }
        }
        for (const v of viewList) { out.push([key, 'canAccessView', v, ctx.canAccessView(v)]); }
      }
    }
  }
  return out;
}

module.exports = function ({ test, assert, eq }) {
  test('UBX-V4 RBAC: decisões das regras can* idênticas antes e depois (matriz completa)', () => {
    const current = fs.readFileSync(APP, 'utf8');
    const frozenPath = path.join(__dirname, 'fixtures', 'app-before-ubx-v4-c.js.txt');
    assert(fs.existsSync(frozenPath), 'fixture com as funções originais (app.js antes da Etapa C) ausente');
    const before = fs.readFileSync(frozenPath, 'utf8');
    const original = decisions(loadOriginal, before, before);
    const now = decisions(loadCurrent, current, before);
    eq(now.length, original.length, 'mesmo tamanho de matriz');
    const diffs = [];
    for (let i = 0; i < original.length; i++) {
      if (JSON.stringify(original[i]) !== JSON.stringify(now[i])) { diffs.push([original[i], now[i]]); }
    }
    eq(diffs.length, 0, `decisões divergentes: ${JSON.stringify(diffs.slice(0, 5))}`);
    assert(original.length > 15000, `matriz grande o bastante (${original.length} decisões)`);
    const trues = original.filter((d) => d[3] === true).length;
    assert(trues > 1000 && trues < original.length - 1000, 'a matriz exercita concessões E negações');
  });

  test('UBX-V4 RBAC: regras puras, sem leitura de estado global, e fórmula da lista ativa igual à do hasPermission', () => {
    const rulesSrc = fs.readFileSync(path.join(JS_ROOT, 'modules', 'auth', 'business', 'access-rules.js'), 'utf8');
    assert(!/__EPI_APP_STATE__|document\.|\bstate\./.test(rulesSrc.replace(/\/\/.*$/gm, '')), 'negócio não lê estado nem DOM');
    const ctxSrc = fs.readFileSync(path.join(JS_ROOT, 'modules', 'auth', 'ui', 'access-context.js'), 'utf8');
    const app = fs.readFileSync(APP, 'utf8');
    const formula = 'state.permissions.length ? state.permissions : normalizePermissions(state.user, [])';
    assert(app.includes(`const activePermissions = ${formula};`), 'hasPermission do app.js mantém a fórmula');
    assert(ctxSrc.includes(`return ${formula};`), 'o adaptador usa a MESMA fórmula da lista ativa');
    const r = baseContext({ permissions: [], user: null });
    vm.runInContext(rulesSrc, r);
    const rules = r.__EPI_ACCESS_RULES__;
    assert(Object.isFrozen(rules), 'namespace congelado');
    // Negação explícita: sem permissões e sem usuário, nenhuma ação de gestão é liberada.
    const ctx0 = { actor: null, permissions: [] };
    for (const name of ['canManageUser', 'canDeleteUser', 'canPromoteToAdmin', 'canPromoteToGeneralAdmin', 'canDemoteAdmin',
      'canDemoteGeneralAdmin', 'canToggleActive', 'canGenerateRecoveryToken']) {
      eq(rules[name](ctx0, { id: 1, role: 'user', company_id: 1 }), false, `${name} nega sem ator`);
    }
    eq(rules.canConfigureMyCompany(ctx0), false);
    // hasAnyPermission × normalizePermissionList + hasPermission originais.
    const before = fs.readFileSync(path.join(__dirname, 'fixtures', 'app-before-ubx-v4-c.js.txt'), 'utf8').split('\n');
    for (const [perms, query] of [[['b'], 'a b'], [['a'], '  a\tb '], [['c'], 'a b'], [['a'], ['a', 'b']], [['a'], []], [['a'], ''], [['a'], null], [['x y'], 'x y']]) {
      const o = loadOriginal({ user: { role: 'admin' }, permissions: perms }, before.join('\n'));
      eq(rules.hasAnyPermission({ permissions: perms }, query), o.hasPermission(query), `hasAnyPermission(${JSON.stringify(perms)}, ${JSON.stringify(query)})`);
    }
    eq(rules.canAccessCommercialArea({ actor: { role: 'general_admin' }, permissions: ['commercial:view'] }), false, 'comercial só master');
  });
};
