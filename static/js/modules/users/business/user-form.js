'use strict';

// Módulo de negócio: Usuários — formulário (Refatoração UBX-V3, Etapa 6).
//
// As verificações de cliente que o saveUser do app.js fazia antes de enviar
// (mesma ordem, mesmas mensagens — inclusive o texto 'Empresa Usuário.' e o
// U+00AD preexistente de "ví­nculo") e o corpo do PUT de mudança de acesso.
// São espelho de conveniência: quem autoriza é o backend (RBAC e escopo de
// empresa em /api/users).
//
// Puro: tudo por parâmetro. `roleLabels` é o ROLE_LABELS DO APP.JS, passado
// pelo chamador — ele NÃO é igual ao de core/constants.js (que também tem
// certification_readonly), e a regra "perfil válido" sempre usou o do app.js.
(function () {
  if (globalThis.__EPI_MODULE_USERS_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_USERS_BUSINESS_LOADED__ = true;

  // Muta `values` como o saveUser fazia e lança Error na primeira regra violada.
  // `actor` é o state.user do app.js, sem padrão de propósito: sem usuário, o
  // TypeError ("reading 'id'") é o mesmo que o saveUser original lançava.
  function prepareUserFormValues(values, { actor, roleLabels }) {
    values.actor_user_id = actor.id;
    if (['general_admin', 'admin'].includes(actor.role)) { values.company_id = actor.company_id; }

    values.active = Number(values.active || 1);
    if (!String(values.company_id || '').trim()) { throw new Error('Empresa Usuário.'); }
    if (!roleLabels[values.role]) { throw new Error('Perfil inválido.'); }
    const noLink = !String(values.linked_employee_id || '').trim();
    if (['admin', 'user'].includes(values.role) && noLink) {
      throw new Error('Administrador Local e Gestor de EPI devem ser vinculados a um colaborador com unidade.');
    }
    if (noLink && !['master_admin', 'general_admin'].includes(actor.role)) {
      throw new Error('Seu perfil Não permite ví­nculo de colaborador.');
    }
    return values;
  }

  // Corpo do PUT /api/users/{id} usado por promover/rebaixar/ativar/desativar.
  function userAccessUpdatePayload(target, changes, actorUserId) {
    return {
      actor_user_id: actorUserId,
      username: target.username,
      full_name: target.full_name,
      password: '',
      role: changes.role || target.role,
      company_id: changes.company_id === undefined ? target.company_id : changes.company_id,
      active: changes.active === undefined ? target.active : changes.active
    };
  }

  globalThis.__EPI_USERS_BUSINESS__ = Object.freeze({ prepareUserFormValues, userAccessUpdatePayload });
})();
