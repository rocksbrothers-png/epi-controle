'use strict';

// Ficha 360° de EPI — integração HTTP (F1, camada integrations).
//
// ÚNICO lugar do domínio com HTTP (guarda static/js/test/employee-ppe-360-boundary.js).
// Usa o cliente único (globalThis.api), resolvido na CHAMADA. Caminho e método
// literais: tests/test_frontend_api_contract.py confronta com o router.
//
// Devolve sempre um ENVELOPE ({ok, data} / {ok:false, error:{code}}), que é o
// que o ciclo de vida da F0 valida (business.readEnvelope). Erro de rede ou de
// HTTP sem código vira REQUEST_FAILED — nunca "vazio". Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_INTEGRATIONS_LOADED__ = true;

  // Resumo da Ficha (F1): identificação, responsáveis e indicadores — UMA
  // requisição por abertura. Autorização, escopo e auditoria ficam no backend.
  async function loadSummary(employeeId, actorUserId) {
    const id = encodeURIComponent(String(employeeId));
    const actor = encodeURIComponent(String(actorUserId || ''));
    try {
      const data = await globalThis.api(`/api/employees/${id}/ppe-360/summary?actor_user_id=${actor}`);
      return { ok: true, data };
    } catch (err) {
      const code = err && typeof err.code === 'string' && err.code ? err.code : 'REQUEST_FAILED';
      return { ok: false, error: { code } };
    }
  }

  globalThis.__EPI_EMPLOYEE_PPE_360_API__ = Object.freeze({ loadSummary });
})();
