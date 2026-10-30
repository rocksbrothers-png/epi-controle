'use strict';

// Módulo de negócio: regras de acesso da interface (Refatoração UBX-V4, Etapa C —
// extraídas de static/app.js).
//
// IMPORTANTE: estas regras só decidem o que a INTERFACE mostra (botões, abas,
// telas). Não substituem a autorização obrigatória do backend, que continua
// decidindo cada requisição. Nenhuma decisão foi ampliada nem alterada: cada
// função reproduz a expressão original do app.js, na mesma ordem.
//
// Puro: tudo chega por parâmetro.
// - ctx.actor: o usuário autenticado (state.user) — id, role, company_id;
// - ctx.permissions: a lista de permissões ATIVAS (a mesma que hasPermission
//   do app.js usa: state.permissions, ou o fallback do perfil quando vazia).
//   O adaptador (../ui/access-context.js) a entrega como getter, avaliado só
//   quando a regra a lê — exatamente quando o hasPermission original rodaria;
// - target: o usuário-alvo da ação (gestão de usuários);
// - config (canAccessView): os mapas de permissão/módulo por view, os perfis de
//   configuração e a visibilidade de módulos vigente.
(function () {
  if (globalThis.__EPI_MODULE_ACCESS_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_ACCESS_RULES_LOADED__ = true;

  // Mesma semântica de normalizePermissionList + hasPermission do app.js: lista
  // explícita ou string separada por espaços; basta UMA das permissões.
  function hasAnyPermission(ctx, permission) {
    const list = Array.isArray(permission) ? permission : String(permission || '').split(/\s+/).filter(Boolean);
    const active = ctx.permissions;
    return list.some((p) => active.includes(p));
  }

  function sameCompany(ctx, target) {
    return String(target.company_id || '') === String(ctx.actor?.company_id || '');
  }

  // ── Gestão de usuários (botões por linha) ─────────────────────────────────
  function canManageUser(ctx, target) {
    if (!hasAnyPermission(ctx, 'users:update')) {return false;}
    if (ctx.actor?.role === 'master_admin') {return target.role !== 'master_admin';}
    if (ctx.actor?.role === 'general_admin') {return ['registry_admin', 'admin', 'user', 'employee'].includes(target.role) && sameCompany(ctx, target);}
    if (ctx.actor?.role === 'registry_admin') {return ['admin', 'user', 'employee'].includes(target.role) && sameCompany(ctx, target);}
    return false;
  }
  function canDeleteUser(ctx, target) { return hasAnyPermission(ctx, 'users:delete') && canManageUser(ctx, target) && String(target.id) !== String(ctx.actor?.id || ''); }
  function canPromoteToAdmin(ctx, target) { return ['master_admin', 'general_admin', 'registry_admin'].includes(ctx.actor?.role) && target.role === 'user' && (ctx.actor?.role === 'master_admin' || sameCompany(ctx, target)); }
  function canPromoteToGeneralAdmin(ctx, target) { return ctx.actor?.role === 'master_admin' && ['admin', 'user'].includes(target.role); }
  function canDemoteAdmin(ctx, target) { return ['master_admin', 'general_admin'].includes(ctx.actor?.role) && target.role === 'admin' && (ctx.actor?.role === 'master_admin' || sameCompany(ctx, target)); }
  function canDemoteGeneralAdmin(ctx, target) { return ctx.actor?.role === 'master_admin' && target.role === 'general_admin'; }
  function canToggleActive(ctx, target) { return canManageUser(ctx, target) && String(target.id) !== String(ctx.actor?.id || ''); }

  function canGenerateRecoveryToken(ctx, target) {
    if (ctx.actor?.role === 'master_admin') {
      return target.role !== 'master_admin' || String(target.id) === String(ctx.actor?.id);
    }
    if (ctx.actor?.role === 'general_admin') {
      return ['registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'].includes(target.role) && sameCompany(ctx, target);
    }
    return false;
  }

  // ── Áreas ─────────────────────────────────────────────────────────────────
  // canManageUsers, canManageEpi e canViewReports não têm chamador no front
  // hoje (registrado em docs/UBX_APPJS_AUDITORIA.md §12); seguem publicadas com
  // o nome legado para não mudar a superfície global.
  function canManageUsers(ctx) {
    return hasAnyPermission(ctx, 'users:update') || hasAnyPermission(ctx, 'users:create') || hasAnyPermission(ctx, 'users:delete');
  }
  function canManageEpi(ctx) {
    return hasAnyPermission(ctx, 'epis:create') || hasAnyPermission(ctx, 'epis:update') || hasAnyPermission(ctx, 'epis:delete');
  }
  function canViewReports(ctx) {
    return hasAnyPermission(ctx, 'reports:view');
  }
  function canAccessCommercialArea(ctx) {
    return ctx.actor?.role === 'master_admin' && hasAnyPermission(ctx, 'commercial:view');
  }
  function canConfigureMyCompany(ctx) {
    return Boolean(ctx.actor) && hasAnyPermission(ctx, 'company_settings:update');
  }
  function canPrintPurchaseQrLabels(ctx) {
    return hasAnyPermission(ctx, 'purchase_requests:update') || hasAnyPermission(ctx, 'stock:adjust') || hasAnyPermission(ctx, 'stock:view');
  }
  function canManagePurchaseFunctions(ctx) {
    return ['general_admin', 'registry_admin'].includes(ctx.actor?.role) && hasAnyPermission(ctx, 'unit_links:manage');
  }

  // Corpo do hasConfigurationAccess do app.js, com os perfis por parâmetro.
  function hasConfigurationAccess(ctx, configurationAdminRoles) {
    return configurationAdminRoles.includes(ctx.actor?.role) && hasAnyPermission(ctx, 'settings:view');
  }

  // ── Acesso a views ────────────────────────────────────────────────────────
  // Mesma cascata do canAccessView do app.js: permissão técnica (com a
  // alternativa de Terceirizados), restrições fixas de papel, configuração e,
  // por fim, visibilidade por módulo — que só RESTRINGE, nunca amplia.
  function canAccessView(ctx, view, config) {
    const permission = config.viewPermissions[view];
    if (permission && !hasAnyPermission(ctx, permission)) {
      // ADR-0002 §10 (correção de escopo): Terceirizados e Prestadores abre
      // com employees:create (aba Empresas) OU employees:create_simplified
      // (aba Cadastro de Colaboradores).
      const altPermission = config.viewPermissionAlternatives[view];
      if (!altPermission || !hasAnyPermission(ctx, altPermission)) {return false;}
    }
    const role = ctx.actor?.role;
    // Views de cadastro estrutural: apenas administradores estruturais.
    if (['epis', 'colaboradores', 'unidades', 'usuarios'].includes(view)
        && !['master_admin', 'general_admin', 'registry_admin'].includes(role)) {
      return false;
    }
    // Gestão de colaborador (movimentação entre unidades): administradores +
    // perfis operacionais (Local/Gestor) — fora de module_visibility.
    if (view === 'gestao-colaborador'
        && !['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'].includes(role)) {
      return false;
    }
    if (view === 'configuracao') {return hasConfigurationAccess(ctx, config.configurationAdminRoles);}
    // Visibilidade estrutural por módulo: módulo ausente do mapa é visível;
    // só restringe quando o backend desliga o módulo para o papel.
    const module = config.viewModule[view];
    const visibility = config.moduleVisibility;
    if (module && visibility && Object.prototype.hasOwnProperty.call(visibility, module)) {
      if (visibility[module]) {return true;}
      // Mesma correção acima, agora para o módulo: terceirizados OU
      // terceirizados_colaboradores libera a view.
      const altModule = config.viewModuleAlternatives[view];
      if (altModule && Object.prototype.hasOwnProperty.call(visibility, altModule)) {
        return Boolean(visibility[altModule]);
      }
      return false;
    }
    return true;
  }

  globalThis.__EPI_ACCESS_RULES__ = Object.freeze({
    hasAnyPermission,
    sameCompany,
    canManageUser,
    canDeleteUser,
    canPromoteToAdmin,
    canPromoteToGeneralAdmin,
    canDemoteAdmin,
    canDemoteGeneralAdmin,
    canToggleActive,
    canGenerateRecoveryToken,
    canManageUsers,
    canManageEpi,
    canViewReports,
    canAccessCommercialArea,
    canConfigureMyCompany,
    canPrintPurchaseQrLabels,
    canManagePurchaseFunctions,
    hasConfigurationAccess,
    canAccessView
  });
})();
