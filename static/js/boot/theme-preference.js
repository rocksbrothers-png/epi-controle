'use strict';
// SECURITY-CSP-V1: era um <script> inline no <head> (index.html) e um onsubmit="return false"
// no formulário de login. A CSP aplicada não permite script inline, então os dois vivem aqui.
// Carregado de forma síncrona no <head>, antes do primeiro paint: o tema escuro salvo na sessão
// é aplicado sem piscar o tema claro.
(function () {
  try {
    const prefs = JSON.parse(sessionStorage.getItem('epi-prefs-sessao') || 'null');
    if (prefs && prefs.tema === 'dark') { document.documentElement.setAttribute('data-theme', 'dark'); }
  } catch (e) { /* sessão indisponível: segue no tema padrão */ }
  // O login é feito por handleLogin (app.js). Até o app carregar, o envio nativo do formulário
  // (POST para "#") fica bloqueado, como fazia o onsubmit inline.
  document.addEventListener('submit', (event) => {
    if (event.target && event.target.id === 'login-form') { event.preventDefault(); }
  }, true);
}());
