'use strict';
/* global tr, showToast --
   globais de views/ui-helpers.js; reportNonCriticalError é global do runtime, resolvidos na chamada */

// UI compartilhada: fluxo "gravar → atualizar a tela" (FIX-NAV-REFRESH-V1).
//
// runExclusiveMutation(key, task): uma única execução por chave enquanto a
//   anterior não termina — clique duplo ou repetição antes do diálogo abrir não
//   reenvia a gravação. Devolve undefined para a chamada ignorada.
// refreshAfterMutation(refresh): roda a atualização da tela DEPOIS de uma
//   gravação já concluída. Se ela falhar, a gravação não vira "falha": mostra o
//   aviso verdadeiro (mutation.refreshFailed) e devolve false — quem chama não
//   repete a operação. 401/403 já encerram a sessão em loadBootstrap.
// coalesceLoad(key, load): durante uma atualização aberta por
//   refreshAfterMutation, a mesma lista pedida duas vezes (pela tela reaberta
//   em showView e pela própria operação) gera uma só requisição. Fora dessa
//   janela é transparente. Dentro dela, só junta leituras da mesma "época de
//   escrita" do api-client: qualquer gravação iniciada ou concluída depois da
//   leitura em andamento (deste fluxo ou de outro) força uma leitura nova.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_MUTATION_FLOW_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_MUTATION_FLOW_LOADED__ = true;

  const inFlight = new Set();
  let activeRefresh = null;

  async function runExclusiveMutation(key, task) {
    if (inFlight.has(key)) {return undefined;}
    inFlight.add(key);
    try {
      return await task();
    } finally {
      inFlight.delete(key);
    }
  }

  // Época de escrita do cliente HTTP (modules/api-client.js). Sem ela, nada é
  // reaproveitado (NaN nunca é igual a si mesmo).
  function currentWriteEpoch() {
    return typeof globalThis.apiWriteEpoch === 'function' ? globalThis.apiWriteEpoch() : NaN;
  }

  function coalesceLoad(key, load) {
    const scope = activeRefresh;
    if (!scope) {return load();}
    const epoch = currentWriteEpoch();
    const pending = scope.loads.get(key);
    // Só junta leituras da MESMA época: se qualquer gravação (deste fluxo ou de
    // outro) começou ou terminou depois da leitura em andamento, uma nova é feita.
    if (pending && pending.epoch === epoch) {return pending.promise;}
    const entry = { epoch, promise: Promise.resolve().then(load) };
    scope.loads.set(key, entry);
    return entry.promise;
  }

  async function refreshAfterMutation(refresh) {
    const scope = { loads: new Map() };
    activeRefresh = scope;
    try {
      await refresh();
      return true;
    } catch (error) {
      reportNonCriticalError('[mutation] gravação concluída, atualização da tela falhou', error);
      if (![401, 403].includes(Number(error?.status || 0))) {
        showToast(tr('mutation.refreshFailed',
          'A operação foi registrada, mas não foi possível atualizar a tela. Recarregue a página para ver os dados atualizados.'), 'warning');
      }
      return false;
    } finally {
      if (activeRefresh === scope) {activeRefresh = null;}
    }
  }

  const api = { runExclusiveMutation, coalesceLoad, refreshAfterMutation };
  for (const [name, fn] of Object.entries(api)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_MUTATION_FLOW__ = Object.freeze({ ...api });
})();
