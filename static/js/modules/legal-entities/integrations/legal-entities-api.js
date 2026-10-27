'use strict';

// Integração: CNPJs (Multi-CNPJ) — endpoints (Refatoração UBX-V5, Etapa 2).
//
// A chamada que o app.js fazia direto, pelo cliente único (globalThis.api)
// resolvido na CHAMADA. Mesmo método, caminho e query. Caminho e método
// LITERAIS: tests/test_frontend_api_contract.py confronta a chamada com as
// rotas do router. Cadastro e edição seguem pelo saveSimpleForm do app.js.
// Autorização (legal_entities:*), regra do último CNPJ ativo e isolamento por
// empresa continuam no backend. Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_LEGAL_ENTITIES_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_LEGAL_ENTITIES_INTEGRATIONS_LOADED__ = true;

  // Inativa (não exclui): o backend preserva o histórico jurídico e fiscal.
  function deactivateLegalEntity(entityId, actorQueryString) {
    return globalThis.api(`/api/legal-entities/${entityId}?${actorQueryString}`, { method: 'DELETE' });
  }

  globalThis.__EPI_LEGAL_ENTITIES_API__ = Object.freeze({ deactivateLegalEntity });
})();
