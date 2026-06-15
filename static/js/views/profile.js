'use strict';

(function () {
  if (globalThis.__EPI_MODULE_PROFILE_LOADED__) { return; }
  globalThis.__EPI_MODULE_PROFILE_LOADED__ = true;

  // ── Local wrappers ─────────────────────────────────────────────────────────
  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function api(path, opts) {
    if (typeof globalThis.api === 'function') { return globalThis.api(path, opts); }
    const options = opts || {};
    if (!options.headers) { options.headers = {}; }
    return fetch(path, options).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) { throw new Error(data?.error || data?.message || `HTTP ${r.status}`); }
      return data;
    });
  }

  // ── Implementations ────────────────────────────────────────────────────────

  function toggleRecoveryPanel() {
    const refs = getRefs();
    if (!refs.recoveryPanel) { return; }
    const isVisible = refs.recoveryPanel.style.display !== 'none';
    refs.recoveryPanel.style.display = isVisible ? 'none' : 'block';
  }

  async function handlePasswordRecovery() {
    const refs = getRefs();
    try {
      const payload = {
        username: String(refs.recoveryUsername?.value || '').trim(),
        new_password: String(refs.recoveryPassword?.value || '').trim(),
        recovery_key: String(refs.recoveryKey?.value || '').trim()
      };
      await api('/api/recover-password', { method: 'POST', body: JSON.stringify(payload) });
      alert('Senha redefinida com sucesso. Faça login com a nova senha.');
      if (refs.recoveryPanel) { refs.recoveryPanel.style.display = 'none'; }
      const passwordField = refs.loginPassword;
      if (passwordField) { passwordField.value = ''; }
    } catch (error) {
      alert(error.message);
    }
  }

  async function handleEmailRecoveryRequest() {
    const btn = document.getElementById('recovery-send-email');
    const username = String(document.getElementById('recovery-email-username')?.value || '').trim();
    if (!username) { alert('Informe o nome de usuário.'); return; }
    if (btn) { btn.disabled = true; }
    try {
      await api('/api/auth/request-email-recovery', { method: 'POST', body: JSON.stringify({ username }) });
      alert('Se o usuário existir com e-mail configurado, a chave de recuperação foi enviada por e-mail.');
    } catch (error) {
      alert(error.message);
    } finally {
      if (btn) { btn.disabled = false; }
    }
  }

  async function generateRecoveryToken(userId) {
    const state = getState();
    try {
      const data = await api(`/api/users/${userId}/recovery-token`, {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user?.id })
      });
      const modal = document.getElementById('recovery-token-modal');
      const tokenEl = document.getElementById('recovery-token-value');
      if (tokenEl) { tokenEl.textContent = data.token || ''; }
      if (modal) { modal.removeAttribute('hidden'); }
    } catch (error) {
      alert(error.message);
    }
  }

  function openMasterProfileModal() {
    const state = getState();
    const modal = document.getElementById('master-profile-modal');
    if (!modal) { return; }
    const emailField = document.getElementById('master-profile-email');
    if (emailField) { emailField.value = state.user?.email || ''; }
    const fbEl = document.getElementById('master-profile-feedback');
    if (fbEl) { fbEl.textContent = ''; }
    modal.removeAttribute('hidden');
  }

  async function saveMasterProfileEmail() {
    const state = getState();
    const emailField = document.getElementById('master-profile-email');
    const fbEl = document.getElementById('master-profile-feedback');
    const email = String(emailField?.value || '').trim();
    try {
      await api(`/api/users/${state.user?.id}/email`, {
        method: 'PUT',
        body: JSON.stringify({ actor_user_id: state.user?.id, email })
      });
      if (state.user) { state.user.email = email; }
      if (fbEl) { fbEl.textContent = 'E-mail salvo com sucesso.'; fbEl.className = 'form-feedback success'; }
    } catch (error) {
      if (fbEl) { fbEl.textContent = error.message; fbEl.className = 'form-feedback error'; }
    }
  }

  async function handleMasterPasswordChange() {
    const state = getState();
    const curPwd = String(document.getElementById('master-current-password')?.value || '').trim();
    const newPwd = String(document.getElementById('master-new-password')?.value || '').trim();
    const confPwd = String(document.getElementById('master-confirm-password')?.value || '').trim();
    const fbEl = document.getElementById('master-profile-feedback');
    try {
      if (!curPwd) { throw new Error('Informe a senha atual.'); }
      if (!newPwd) { throw new Error('Informe a nova senha.'); }
      if (newPwd.length < 6) { throw new Error('A nova senha deve ter pelo menos 6 caracteres.'); }
      if (newPwd !== confPwd) { throw new Error('As senhas não conferem.'); }
      await api('/api/change-password', {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user?.id, current_password: curPwd, new_password: newPwd })
      });
      if (fbEl) { fbEl.textContent = 'Senha atualizada com sucesso.'; fbEl.className = 'form-feedback success'; }
      document.getElementById('master-current-password').value = '';
      document.getElementById('master-new-password').value = '';
      document.getElementById('master-confirm-password').value = '';
    } catch (error) {
      if (fbEl) { fbEl.textContent = error.message; fbEl.className = 'form-feedback error'; }
    }
  }

  // ── Exports ────────────────────────────────────────────────────────────────
  const moduleExports = {
    toggleRecoveryPanel,
    handlePasswordRecovery,
    handleEmailRecoveryRequest,
    generateRecoveryToken,
    openMasterProfileModal,
    saveMasterProfileEmail,
    handleMasterPasswordChange
  };

  for (const [name, fn] of Object.entries(moduleExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_PROFILE__ = Object.freeze({ ...moduleExports });
})();
