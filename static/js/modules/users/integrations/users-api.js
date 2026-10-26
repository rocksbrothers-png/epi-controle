'use strict';

// Integração: Usuários — endpoints (Refatoração UBX-V3, Etapa 6).
//
// As chamadas de gestão de usuários que o app.js fazia direto, pelo cliente
// único (globalThis.api) resolvido na CHAMADA. Mesmos métodos, caminhos, query
// e corpos. Autorização, RBAC e isolamento por empresa continuam no backend.
// Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_USERS_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_USERS_INTEGRATIONS_LOADED__ = true;

  // editingUserId vazio → POST /api/users; senão PUT /api/users/{id}.
  function saveUser(editingUserId, values) {
    return globalThis.api(editingUserId ? `/api/users/${editingUserId}` : '/api/users',
      { method: editingUserId ? 'PUT' : 'POST', body: JSON.stringify(values) });
  }

  function updateUser(userId, payload) {
    return globalThis.api(`/api/users/${userId}`, { method: 'PUT', body: JSON.stringify(payload) });
  }

  // actorQueryString: o actorQuery() do app.js (escopo do ator).
  function deleteUser(userId, actorQueryString) {
    return globalThis.api(`/api/users/${userId}?${actorQueryString}`, { method: 'DELETE' });
  }

  globalThis.__EPI_USERS_API__ = Object.freeze({ saveUser, updateUser, deleteUser });
})();
