'use strict';
(function () {
  function decide(api, jobId, operation, actorUserId) {
    if (operation === 'homologate') {
      return api(`/api/data-migration/jobs/${encodeURIComponent(jobId)}/homologate`, {
        method: 'POST', body: JSON.stringify({ actor_user_id: actorUserId }),
      });
    }
    if (operation === 'revert') {
      return api(`/api/data-migration/jobs/${encodeURIComponent(jobId)}/revert`, {
        method: 'POST', body: JSON.stringify({ actor_user_id: actorUserId }),
      });
    }
    throw new Error('Decisão de migração inválida.');
  }
  globalThis.__EPI_MIGRATION_DECISIONS__ = Object.freeze({ decide });
})();
