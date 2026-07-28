'use strict';

// Tela de CNPJs do web legado — regras puras.
//
// Segue o padrão dos demais módulos extraídos: aqui ficam filtro, rótulos e
// montagem de linha (funções sem DOM e sem estado global, testadas no
// harness); app.js faz a leitura do estado e a escrita no documento.
//
// A tela existe porque o web legado não tinha **nenhuma** forma de cadastrar
// ou consultar CNPJ: o recurso existia no backend e no app, e quem usa o
// legado simplesmente não alcançava o Multi-CNPJ.
(function () {
  if (globalThis.__EPI_MODULE_LEGAL_ENTITIES_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_LEGAL_ENTITIES_VIEW_LOADED__ = true;

  /** `active` chega como 0/1 no SQLite e booleano no Postgres. */
  function isActive(entity) {
    const value = entity?.active;
    return value === true || value === 1 || value === '1';
  }

  var TYPE_LABELS = {
    matriz: 'Matriz',
    filial: 'Filial',
    subsidiaria: 'Subsidiária',
    spe: 'SPE',
    jv_partner: 'Sócia de JV',
    consorciada: 'Consorciada',
    outro: 'Outro',
  };

  /** Rótulo do tipo; valor desconhecido volta como veio, em vez de sumir. */
  function entityTypeLabel(value) {
    const key = String(value || '').trim();
    return TYPE_LABELS[key] || key || '-';
  }

  /**
   * Linhas visíveis da tabela.
   *
   * Inativos ficam ocultos por padrão — o histórico é preservado, mas o CNPJ
   * não deve mais ser usado em novas operações e polui a lista de trabalho.
   * A busca cobre número, razão social e nome fantasia, que são as três formas
   * pelas quais alguém procura um CNPJ.
   */
  function visibleLegalEntities(entities, options) {
    const showInactive = Boolean(options?.showInactive);
    const type = String(options?.type || '').trim();
    const term = String(options?.search || '').trim().toLowerCase();
    return (Array.isArray(entities) ? entities : []).filter((item) => {
      if (!showInactive && !isActive(item)) { return false; }
      if (type && String(item?.entity_type || '') !== type) { return false; }
      if (!term) { return true; }
      const haystack = [item?.cnpj, item?.legal_name, item?.trade_name]
        .map((value) => String(value || '').toLowerCase())
        .join(' ');
      return haystack.includes(term);
    });
  }

  /**
   * Só o último CNPJ ativo não pode ser inativado — a empresa ficaria sem
   * nenhuma pessoa jurídica, e todo colaborador perderia o vínculo.
   *
   * O backend também recusa (é ele quem decide); esconder o botão aqui evita
   * oferecer uma ação que só produziria mensagem de erro.
   */
  function canDeactivate(entity, entities) {
    if (!isActive(entity)) { return false; }
    const actives = (Array.isArray(entities) ? entities : []).filter(isActive);
    return actives.length > 1;
  }

  globalThis.__EPI_LEGAL_ENTITIES_VIEW__ = Object.freeze({
    entityTypeLabel,
    visibleLegalEntities,
    canDeactivate,
    isActive,
  });
})();
