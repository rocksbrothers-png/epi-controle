'use strict';
/* global tr, escapeHtml, preferenciasDoPrincipal, hasConfigurationAccess, navigateToView, isSpaNavigationEnabled, bindAppListener, _applySettings */
// Shell/Topbar UBX: contexto lido na chamada; preferências e autorização mantêm seus donos.
(function () {
  if (globalThis.__EPI_MODULE_SETTINGS_DRAWER_LOADED__) { return; }
  globalThis.__EPI_MODULE_SETTINGS_DRAWER_LOADED__ = true;

  function applyTableDensityPref() {
    document.body?.classList.toggle('ux-density-compact', preferenciasDoPrincipal().densidade === 'compact');
  }

  function _settingsDrawerBodyHtml() {
    const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const lang = (globalThis.EpiI18n && globalThis.EpiI18n.lang) || 'pt-BR';
    const density = preferenciasDoPrincipal().densidade;
    const langs = [['pt-BR', 'Português'], ['en-GB', 'English'], ['es-ES', 'Español'], ['fr-FR', 'Français'], ['nb-NO', 'Bokmål']];
    const opt = (v, cur, label) => `<option value="${v}"${v === cur ? ' selected' : ''}>${escapeHtml(label)}</option>`;
    const advanced = hasConfigurationAccess()
      ? `<button type="button" class="ghost settings-advanced" id="settings-advanced">${tr('settings.advanced', 'Configurações avançadas')}</button>`
      : '';
    return `<div class="settings-drawer">
    <label class="settings-field"><span>${tr('settings.theme', 'Tema')}</span>
      <select id="settings-theme">${opt('light', theme, tr('settings.themeLight', 'Claro'))}${opt('dark', theme, tr('settings.themeDark', 'Escuro'))}</select></label>
    <label class="settings-field"><span>${tr('settings.language', 'Idioma')}</span>
      <select id="settings-language">${langs.map(([c, n]) => opt(c, lang, n)).join('')}</select></label>
    <label class="settings-field"><span>${tr('settings.density', 'Densidade da tabela')}</span>
      <select id="settings-density">${opt('normal', density, tr('settings.densityNormal', 'Normal'))}${opt('compact', density, tr('settings.densityCompact', 'Compacta'))}</select></label>
    <p class="hint">${tr('settings.hint', 'As preferências são salvas na sua conta e acompanham você em qualquer dispositivo.')}</p>
    ${advanced}
  </div>`;
  }

  function _settingsDrawerFooterHtml() {
    return `<button type="button" class="ghost" id="settings-restore">${tr('settings.restore', 'Restaurar padrão')}</button>`
      + '<span style="flex:1"></span>'
      + `<button type="button" class="ghost" id="settings-cancel">${tr('cancel', 'Cancelar')}</button>`
      + `<button type="button" class="primary" id="settings-save">${tr('save', 'Salvar')}</button>`;
  }

  function openSettingsDrawer() {
    if (typeof globalThis.dsOpenDrawer !== 'function') {
      // Fallback (drawer indisponível): mantém o acesso à página de configuração.
      if (hasConfigurationAccess()) {
        navigateToView('configuracao', { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: false });
      }
      return;
    }
    globalThis.dsOpenDrawer({
      title: tr('settings.title', 'Configurações'),
      bodyHtml: _settingsDrawerBodyHtml(),
      footerHtml: _settingsDrawerFooterHtml(),
    });
    const root = document.getElementById('ds-drawer-root');
    if (!root) { return; }
    const val = (sel, fallback) => root.querySelector(sel)?.value || fallback;
    bindAppListener(root.querySelector('#settings-save'), 'click', () => {
      _applySettings({
        theme: val('#settings-theme', 'light'),
        lang: val('#settings-language', 'pt-BR'),
        density: val('#settings-density', 'normal'),
      });
      globalThis.dsCloseDrawer();
    });
    bindAppListener(root.querySelector('#settings-cancel'), 'click', () => globalThis.dsCloseDrawer());
    bindAppListener(root.querySelector('#settings-restore'), 'click', () => {
      // Reseta os campos para o padrão; o usuário confirma em Salvar.
      if (root.querySelector('#settings-theme')) { root.querySelector('#settings-theme').value = 'light'; }
      if (root.querySelector('#settings-language')) { root.querySelector('#settings-language').value = 'pt-BR'; }
      if (root.querySelector('#settings-density')) { root.querySelector('#settings-density').value = 'normal'; }
    });
    bindAppListener(root.querySelector('#settings-advanced'), 'click', () => {
      globalThis.dsCloseDrawer();
      navigateToView('configuracao', { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: false });
    });
  }

  const exports = { applyTableDensityPref, _settingsDrawerBodyHtml, _settingsDrawerFooterHtml, openSettingsDrawer };
  for (const [name, fn] of Object.entries(exports)) { globalThis[name] = fn; }
  globalThis.__EPI_SETTINGS_DRAWER_UI__ = Object.freeze({ ...exports });
})();
