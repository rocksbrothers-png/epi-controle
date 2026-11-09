'use strict';
/* global isUxMobileEnabled, preferenciasDoPrincipal, definirPreferencias */
// Shell/Topbar UBX: contexto lido na chamada; preferências e autorização mantêm seus donos.
(function () {
  if (globalThis.__EPI_MODULE_SHELL_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHELL_VIEW_LOADED__ = true;

  function closeMobileMenu() {
    const refs = globalThis.__EPI_REFS__;
    document.body?.classList.remove('mobile-menu-open');
    if (refs.mobileMenuToggle) {refs.mobileMenuToggle.setAttribute('aria-expanded', 'false');}
  }

  function openMobileMenu() {
    const refs = globalThis.__EPI_REFS__;
    document.body?.classList.add('mobile-menu-open');
    if (refs.mobileMenuToggle) {refs.mobileMenuToggle.setAttribute('aria-expanded', 'true');}
  }

  function applyMobileUxVisibility() {
    const refs = globalThis.__EPI_REFS__;
    const enabled = isUxMobileEnabled();
    document.body?.classList.toggle('ux-mobile-enabled', enabled);
    if (!enabled) {closeMobileMenu();}
    // O botão ☰ passa a ser sempre visível: no mobile abre/fecha a gaveta; no
    // desktop recolhe/expande a sidebar (auditoria Navegação §6).
    if (refs.mobileMenuToggle) {refs.mobileMenuToggle.hidden = false;}
    applySidebarCollapsed();
  }

  function isSidebarCollapsedPref() {
    return preferenciasDoPrincipal().sidebar === 'collapsed';
  }

  function applySidebarCollapsed() {
    const refs = globalThis.__EPI_REFS__;
    // O colapso mini-rail só se aplica fora do modo mobile (lá a sidebar é gaveta).
    const collapsed = !isUxMobileEnabled() && isSidebarCollapsedPref();
    document.body?.classList.toggle('sidebar-collapsed', collapsed);
    if (refs.mobileMenuToggle && !isUxMobileEnabled()) {
      refs.mobileMenuToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      refs.mobileMenuToggle.setAttribute(
        'aria-label',
        collapsed ? trEpi('nav.expandMenu', 'Expandir menu') : trEpi('nav.collapseMenu', 'Recolher menu'),
      );
    }
  }

  function toggleSidebarCollapsed() {
    // `definirPreferencias` já reaplica a tela e persiste no servidor.
    definirPreferencias({ sidebar: isSidebarCollapsedPref() ? 'expanded' : 'collapsed' });
  }

  function applyMenuGroupVisibility() {
    const menu = document.getElementById('menu');
    if (!menu) {return;}
    const children = Array.from(menu.children);
    let currentLabel = null;
    let groupHasVisible = false;
    const commit = () => { if (currentLabel) {currentLabel.style.display = groupHasVisible ? '' : 'none';} };
    children.forEach((node) => {
      if (node.matches('[data-menu-group]')) {
        commit();
        currentLabel = node;
        groupHasVisible = false;
      } else if (node.classList.contains('menu-link') && node.style.display !== 'none') {
        groupHasVisible = true;
      }
    });
    commit();
  }

  const exports = { closeMobileMenu, openMobileMenu, applyMobileUxVisibility, isSidebarCollapsedPref, applySidebarCollapsed, toggleSidebarCollapsed, applyMenuGroupVisibility };
  for (const [name, fn] of Object.entries(exports)) { globalThis[name] = fn; }
  globalThis.__EPI_SHELL_UI__ = Object.freeze({ ...exports });
})();
