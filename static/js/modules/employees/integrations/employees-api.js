'use strict';

// Integração: Colaboradores — endpoints (Refatoração UBX-V4, Etapa B1).
//
// Chamadas que o app.js fazia direto, pelo cliente único (globalThis.api)
// resolvido na CHAMADA. Mesmo método, caminho e corpo. Autorização e
// isolamento por empresa continuam no backend. Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEES_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEES_INTEGRATIONS_LOADED__ = true;

  // Gera o link (token) do portal externo do colaborador.
  function createEmployeePortalLink(actorUserId, employeeId) {
    return globalThis.api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId, employee_id: Number(employeeId) })
    });
  }

  globalThis.__EPI_EMPLOYEES_API__ = Object.freeze({ createEmployeePortalLink });
})();
