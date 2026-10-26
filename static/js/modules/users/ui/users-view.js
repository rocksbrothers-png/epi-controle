'use strict';
/* global tr, USER_COMPANY_REQUIRED_ROLES, filterByUserCompany, populateLinkedEmployeeOptions, syncUserEmployeeLink,
   canManageUser, canDeleteUser, canPromoteToAdmin, canPromoteToGeneralAdmin, canDemoteAdmin, canDemoteGeneralAdmin,
   canGenerateRecoveryToken, canToggleActive, addEmployeeButtons, populateRoleOptions, loadBootstrap, renderTables,
   confirmDestructive, actorQuery --
   globais do app.js e de core/constants.js, resolvidos na chamada (ver abaixo) */

// UI: Usuários — gestão (Refatoração UBX-V3, Etapa 6 — extraído de static/app.js).
//
// Filtros e resumo da lista, feedback e campos do formulário, botões de ação
// por linha e mudanças de acesso (promover/rebaixar/ativar/desativar).
//
// RBAC: os botões continuam decididos pelas MESMAS funções can* do app.js
// (canManageUser, canPromoteToAdmin, … — fallback visual; a autorização efetiva
// é do backend). Elas não saíram nesta etapa (fallback de RBAC fica por último).
// Estado e refs: os MESMOS objetos do app.js, lidos na chamada.
// ROLE_LABELS/USER_COMPANY_REQUIRED_ROLES daqui são os globais de
// core/constants.js: USER_COMPANY_REQUIRED_ROLES é idêntico ao do app.js, e
// ROLE_LABELS só é usado como texto padrão dos 8 perfis do filtro, iguais nos
// dois (o de core/constants.js tem também certification_readonly — por isso a
// validação do saveUser, que fica no app.js, segue usando o ROLE_LABELS dele).
// updateUserAccess (e, desde a UBX-V4, deleteUser) eram `async function` de bloco no app.js; agora são globais.
(function () {
  if (globalThis.__EPI_MODULE_USERS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_USERS_UI_LOADED__ = true;

  function usersBusiness() { return globalThis.__EPI_USERS_BUSINESS__; }
  function usersApi() { return globalThis.__EPI_USERS_API__; }

  function populateUserFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.userFilterCompany) {return;}
    const all = tr('user.filterAll', 'Todos');
    const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
    const optionsHtml = companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
    refs.userFilterCompany.innerHTML = `<option value="">${all}</option>` + optionsHtml;
    const roleKeys = ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'];
    refs.userFilterRole.innerHTML = `<option value="">${all}</option>` +
      roleKeys.map((k) => `<option value="${k}">${tr('role.' + k, ROLE_LABELS[k] || k)}</option>`).join('');
    refs.userFilterStatus.innerHTML = `<option value="">${all}</option>` +
      `<option value="1">${tr('user.active', 'Ativo')}</option>` +
      `<option value="0">${tr('user.inactive', 'Inativo')}</option>`;
    refs.userFilterCompany.value = state.userFilters.company_id;
    refs.userFilterRole.value = state.userFilters.role;
    refs.userFilterStatus.value = state.userFilters.active;
    refs.userFilterSearch.value = state.userFilters.search;
  }

  function renderUsersSummary() {
    const refs = globalThis.__EPI_REFS__;
    const visible = filteredUsers();
    const admins = visible.filter((item) => ['master_admin', 'general_admin', 'admin'].includes(item.role)).length;
    const active = visible.filter((item) => Number(item.active) === 1).length;
    refs.usersSummary.innerHTML = [
      [tr('user.kpiVisible', 'Visíveis'), visible.length],
      [tr('user.kpiAdmins', 'Administradores'), admins],
      [tr('user.kpiActive', 'Ativos'), active]
    ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
  }

  function filteredUsers() {
    const state = globalThis.__EPI_APP_STATE__;
    return filterByUserCompany(state.users).filter((item) => {
      if (state.userFilters.company_id && String(item.company_id || '') !== String(state.userFilters.company_id)) {return false;}
      if (state.userFilters.role && item.role !== state.userFilters.role) {return false;}
      if (state.userFilters.active !== '' && String(Number(item.active)) !== String(state.userFilters.active)) {return false;}
      if (state.userFilters.search) {
        const haystack = `${item.full_name} ${item.username} ${item.company_name || ''}`.toLowerCase();
        if (!haystack.includes(state.userFilters.search)) {return false;}
      }
      return true;
    });
  }

  function setUserFormFeedback(message = '', isError = false) {
    const field = document.getElementById('user-form-feedback');
    if (!field) {return;}
    field.textContent = String(message || '');
    field.classList.toggle('error', Boolean(isError));
  }

  function syncUserFormAccess() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const roleField = refs.userForm?.elements?.role;
    const companyField = refs.userForm?.elements?.company_id;
    if (!roleField || !companyField) {return;}

    const selectedRole = String(roleField.value || '').trim();
    const requiresCompany = USER_COMPANY_REQUIRED_ROLES.includes(selectedRole);
    const companyLocked = ['general_admin', 'registry_admin', 'admin'].includes(state.user?.role);

    if (companyLocked) {
      companyField.value = state.user?.company_id || '';
      companyField.disabled = true;
    } else {
      companyField.disabled = !requiresCompany;
      if (!requiresCompany) {companyField.value = '';}
    }

    if (requiresCompany && !companyField.value) {
      companyField.value = String(state.selectedCompanyId || state.user?.company_id || state.companies[0]?.id || '');
    }

    populateLinkedEmployeeOptions();
    syncUserEmployeeLink();
  }

  function userActionButtons(target) {
    if (!canManageUser(target) && !canDeleteUser(target) && target.role !== 'employee') {return '-';}
    const actions = [];

    addEditButtons(actions, target);
    addPromoteButtons(actions, target);
    addPasswordButtons(actions, target);
    addManagementButtons(actions, target);
    addEmployeeButtons(actions, target);

    if (actions.length === 0) {return '-';}
    return `<div class="action-group">${actions.join('')}</div>`;
  }

  function addEditButtons(actions, target) {
    if (canManageUser(target)) {
      actions.push(`<button class="ghost" data-user-edit="${target.id}">${tr('edit', 'Editar')}</button>`);
    }
  }

  function addPromoteButtons(actions, target) {
    if (canPromoteToAdmin(target)) {
      actions.push(`<button class="ghost" data-user-promote-admin="${target.id}">${tr('user.promoteToAdmin', 'Tornar Administrador')}</button>`);
    }
    if (canPromoteToGeneralAdmin(target)) {
      actions.push(`<button class="ghost" data-user-promote-general="${target.id}">${tr('user.promoteToGeneralAdmin', 'Tornar Adm. Geral')}</button>`);
    }
    if (canDemoteGeneralAdmin(target)) {
      actions.push(`<button class="ghost" data-user-demote-general="${target.id}">${tr('user.removeFromGeneral', 'Remover do Geral')}</button>`);
    }
    if (canDemoteAdmin(target)) {
      actions.push(`<button class="ghost" data-user-demote-admin="${target.id}">${tr('user.demoteToUser', 'Rebaixar para Usuário')}</button>`);
    }
  }

  function addPasswordButtons(actions, target) {
    if (canManageUser(target)) {
      actions.push(
        `<button class="ghost" data-user-temp-password="${target.id}">${tr('user.generateProvPassword', 'Gerar senha provisória')}</button>`,
        `<button class="ghost" data-user-generate-copy-password="${target.id}">${tr('user.generateCopyPassword', 'Gerar e copiar senha')}</button>`
      );
      if (Number(target.force_password_change || 0) !== 1) {
        actions.push(`<button class="ghost" data-user-force-password-change="${target.id}">${tr('user.forcePasswordChange', 'Forçar troca da senha novamente')}</button>`);
      }
    }
    if (canGenerateRecoveryToken(target)) {
      actions.push(`<button class="ghost" data-user-recovery-token="${target.id}">${tr('user.generateRecoveryKey', 'Gerar chave de recuperação')}</button>`);
    }
  }

  function addManagementButtons(actions, target) {
    if (canManageUser(target)) {
      actions.push(
        `<button class="ghost" data-user-copy-email="${target.id}">${tr('user.copyEmail', 'Copiar e-mail')}</button>`,
        `<button class="ghost" data-user-copy-whatsapp="${target.id}">${tr('user.copyWhatsapp', 'Copiar WhatsApp')}</button>`
      );
    }
    if (canToggleActive(target)) {
      const label = Number(target.active) === 1 ? tr('user.deactivate', 'Desativar Usuário') : tr('user.activate', 'Ativar Usuário');
      actions.push(`<button class="ghost" data-user-toggle="${target.id}">${label}</button>`);
    }
    if (canDeleteUser(target)) {
      actions.push(`<button class="ghost" data-user-delete="${target.id}">${tr('user.remove', 'Remover')}</button>`);
    }
  }

  function startEditUser(userId) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const user = state.users.find((item) => String(item.id) === String(userId));
    if (!user) {return;}
    state.editingUserId = user.id;
    setUserFormFeedback('');
    refs.userForm.elements.id.value = user.id;
    refs.userForm.elements.full_name.value = user.full_name;
    refs.userForm.elements.username.value = user.username;
    refs.userForm.elements.password.value = '';
    populateRoleOptions();
    refs.userForm.elements.role.value = canManageUser(user) ? user.role : refs.userRole.value;
    refs.userForm.elements.company_id.value = user.company_id || '';
    refs.userForm.elements.linked_employee_id.value = user.linked_employee_id || '';
    syncUserFormAccess();
  }

  async function updateUserAccess(userId, changes, successMessage = '') {
    const state = globalThis.__EPI_APP_STATE__;
    const target = state.users.find((item) => String(item.id) === String(userId));
    if (!target) {return;}
    try {
      await usersApi().updateUser(userId, usersBusiness().userAccessUpdatePayload(target, changes, state.user.id));
      if (successMessage) {alert(successMessage);}
      setUserFormFeedback(successMessage || 'Usuário atualizado com sucesso.');
      await loadBootstrap();
    } catch (error) {
      setUserFormFeedback(error.message, true);
      alert(error.message);
    }
  }

  // Saiu do app.js na UBX-V4 (Etapa A), quando confirmDestructive virou global.
  async function deleteUser(userId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!(await confirmDestructive({ title: 'Remover usuário', message: 'Deseja remover este usuário?', confirmLabel: 'Remover', variant: 'danger' }))) {return;}
    try {
      await usersApi().deleteUser(userId, actorQuery());
      if (String(state.editingUserId || '') === String(userId)) {resetUserForm();}
      setUserFormFeedback('Usuário removido com sucesso.');
      await loadBootstrap();
    } catch (error) {
      setUserFormFeedback(error.message, true);
      alert(error.message);
    }
  }

  function resetUserForm() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.editingUserId = null;
    refs.userForm.reset();
    if (refs.userLinkedEmployeeSearch) {refs.userLinkedEmployeeSearch.value = '';}
    setUserFormFeedback('');
    refs.userForm.elements.id.value = '';
    populateRoleOptions();
    syncUserFormAccess();
  }

  function syncUserFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.userFilters.company_id = refs.userFilterCompany.value;
    state.userFilters.role = refs.userFilterRole.value;
    state.userFilters.active = refs.userFilterStatus.value;
    state.userFilters.search = refs.userFilterSearch.value.trim().toLowerCase();
    renderTables();
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const usersViewExports = {
    populateUserFilters,
    renderUsersSummary,
    filteredUsers,
    setUserFormFeedback,
    syncUserFormAccess,
    userActionButtons,
    addEditButtons,
    addPromoteButtons,
    addPasswordButtons,
    addManagementButtons,
    startEditUser,
    updateUserAccess,
    deleteUser,
    resetUserForm,
    syncUserFilters
  };

  for (const [name, fn] of Object.entries(usersViewExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_USERS_VIEW__ = Object.freeze({ ...usersViewExports });
})();
