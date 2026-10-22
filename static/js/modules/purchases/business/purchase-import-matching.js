'use strict';

// Módulo de negócio: Compras — conciliação da importação de cotação/PO
// (Refatoração UBX — camada Business, extraída de static/app.js).
//
// Regras puras usadas ao importar o arquivo de cotação devolvido pelo
// fornecedor: normalizar valores monetários/quantidades em formato BR ou US e
// casar cada linha importada com o item da requisição de compra (por
// `item_id` exato ou, na falta dele, pela melhor pontuação de CA, EPI,
// colaborador, unidade, fornecedor, origem e tamanhos).
//
// Sem DOM, sem HTTP, sem estado global: toda entrada vem por parâmetro.
// Consumidor: static/js/views/purchases.js (via globalThis, contrato legado).
// O comportamento é idêntico ao das funções originais do app.js — qualquer
// mudança de regra é mudança de negócio, não de estrutura.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_IMPORT_MATCHING_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_IMPORT_MATCHING_LOADED__ = true;

  function _normalizeCa(ca) {
    return String(ca || '').trim().replace(/[-\s]+$/, '').replace(/^[-\s]+/, '').toLowerCase();
  }

  function _parsePurchaseMoney(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return Math.round(value * 100) / 100;
    }
    let text = String(value ?? '').trim();
    if (!text) { return 0; }
    text = text.replace(/\u00a0/g, ' ')
      .replace(/r\$/gi, '')
      .replace(/\s+/g, '')
      .replace(/[^0-9,.-]/g, '');
    if (!text || ['-', ',', '.', '-,', '-.'].includes(text)) { return 0; }
    const negative = text.startsWith('-');
    text = text.replace(/-/g, '');
    const commaIndex = text.lastIndexOf(',');
    const dotIndex = text.lastIndexOf('.');
    let normalized = '';
    if (commaIndex >= 0 || dotIndex >= 0) {
      const decimalSep = commaIndex > dotIndex ? ',' : '.';
      const parts = text.split(decimalSep);
      const fractional = parts.pop() || '0';
      const integer = parts.join('').replace(/[,.]/g, '') || '0';
      normalized = `${negative ? '-' : ''}${integer}.${fractional}`;
    } else {
      normalized = `${negative ? '-' : ''}${text.replace(/[,.]/g, '')}`;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : 0;
  }

  function _parsePurchaseQuantity(value, fallback = 1) {
    const parsed = Number(String(value ?? '').replace(/\u00a0/g, '').replace(',', '.').replace(/[^0-9.-]/g, ''));
    const quantity = Math.round(parsed);
    return Number.isFinite(quantity) && quantity > 0 ? quantity : fallback;
  }

  function _normalizePurchaseText(value) {
    return String(value || '').trim().toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ');
  }

  function _normalizePurchaseSize(value) {
    const text = _normalizePurchaseText(value);
    return (!text || text === 'n/a' || text === 'na') ? '' : text;
  }

  function _normalizePurchaseOrigin(value) {
    const text = _normalizePurchaseText(value);
    if (text.includes('colaborador') || text.includes('employee')) { return 'employee_request'; }
    if (text.includes('estoque') || text.includes('stock')) { return 'stock_minimum'; }
    return text;
  }

  function _scorePurchaseImportMatch(row, item) {
    let score = 0;
    const rowCa = _normalizeCa(row.ca);
    const rowEpi = _normalizePurchaseText(row.epi);
    const rowEmployee = _normalizePurchaseText(row.colaborador);
    const rowUnit = _normalizePurchaseText(row.unidade);
    const rowSupplier = _normalizePurchaseText(row.fornecedor);
    const rowOrigin = _normalizePurchaseOrigin(row.origem);
    const rowSize = _normalizePurchaseSize(row.tamanho);
    const rowGlove = _normalizePurchaseSize(row.tamanho_luva);
    const rowUniform = _normalizePurchaseSize(row.tamanho_uniforme);
    if (rowCa && _normalizeCa(item.ca || item.epi_ca) === rowCa) { score += 4; }
    if (rowEpi && _normalizePurchaseText(item.epi_name || item.epi_display_name) === rowEpi) { score += 3; }
    if (rowEmployee && _normalizePurchaseText(item.employee_name) === rowEmployee) { score += 3; }
    if (rowUnit && _normalizePurchaseText(item.unit_name) === rowUnit) { score += 2; }
    if (rowSupplier && _normalizePurchaseText(item.supplier) === rowSupplier) { score += 1; }
    if (rowOrigin && _normalizePurchaseOrigin(item.origin) === rowOrigin) { score += 1; }
    if (rowSize && _normalizePurchaseSize(item.size) === rowSize) { score += 2; }
    if (rowGlove && _normalizePurchaseSize(item.glove_size) === rowGlove) { score += 2; }
    if (rowUniform && _normalizePurchaseSize(item.uniform_size) === rowUniform) { score += 2; }
    return score;
  }

  function _matchPurchaseImportRows(rows, prItems) {
    const used = new Set();
    return rows.map((row) => {
      const itemId = String(row.item_id || '').trim();
      if (itemId) {
        const exactIndex = prItems.findIndex((item, idx) => !used.has(idx) && String(item.id || item.purchase_request_item_id || '') === itemId);
        if (exactIndex >= 0) {
          used.add(exactIndex);
          return prItems[exactIndex];
        }
      }
      let bestIndex = -1;
      let bestScore = 0;
      prItems.forEach((item, idx) => {
        if (used.has(idx)) { return; }
        const score = _scorePurchaseImportMatch(row, item);
        if (score > bestScore) {
          bestScore = score;
          bestIndex = idx;
        }
      });
      if (bestIndex >= 0 && bestScore > 0) {
        used.add(bestIndex);
        return prItems[bestIndex];
      }
      return null;
    });
  }

  // ── Associação confirmada (opção C + bloqueio A, decisão de 2026-10-22) ──
  //
  // `_matchPurchaseImportRows` (acima) escolhe sozinho o item de maior
  // pontuação e aceita pontuação vinda só de fornecedor/origem. Ele permanece
  // pelo contrato global, mas a importação de cotação usa a avaliação abaixo,
  // que NÃO associa nada por conta própria:
  //   1. fornecedor, origem, colaborador e unidade são contexto, nunca
  //      identidade — sozinhos não tornam um item candidato;
  //   2. CA presente nos dois lados e divergente BLOQUEIA o item;
  //   3. CA ausente: sem sugestão automática, a escolha é manual;
  //   4. CA coincidente não basta para sugerir: precisa também de descrição,
  //      modelo ou id do item coincidente, e de nenhuma divergência;
  //   5. todos os candidatos relevantes são devolvidos, com divergências;
  //   6. só existe sugestão quando ela é única (inclusive entre linhas).
  // A decisão final é sempre do operador, e o backend revalida.

  // CA comparável: só dígitos, sem zeros à esquerda. Sem dígitos ("N/A",
  // "ISENTO", "-") conta como ausente. Mesma regra do backend.
  function _normalizeCaNumber(value) {
    const digits = String(value ?? '').replace(/\D+/g, '');
    return /[1-9]/.test(digits) ? digits.replace(/^0+/, '') : '';
  }

  // O CA do cadastro atual do EPI prevalece sobre o registrado no item.
  function _purchaseItemCa(item) {
    return _normalizeCaNumber(item.epi_ca) || _normalizeCaNumber(item.ca);
  }

  function _purchaseTextRelation(a, b) {
    const left = _normalizePurchaseText(a);
    const right = _normalizePurchaseText(b);
    if (!left || !right) { return 'missing'; }
    if (left === right) { return 'equal'; }
    const leftTokens = left.split(' ').filter((t) => t.length > 1);
    const rightTokens = right.split(' ').filter((t) => t.length > 1);
    if (!leftTokens.length || !rightTokens.length) { return 'different'; }
    const contains = (outer, inner) => inner.every((t) => outer.includes(t));
    return contains(rightTokens, leftTokens) || contains(leftTokens, rightTokens) ? 'partial' : 'different';
  }

  function _evaluatePurchaseImportCandidate(row, item) {
    const matches = [];
    const divergences = [];
    const contradictions = [];
    let blocked = false;
    let blockReason = '';

    const rowItemId = String(row.item_id ?? '').trim();
    const itemId = String(item.id ?? item.purchase_request_item_id ?? '');
    if (rowItemId) {
      if (rowItemId === itemId) {
        matches.push('id do item');
      } else {
        const message = `id do item no arquivo (${rowItemId}) é de outro item`;
        divergences.push(message);
        contradictions.push(message);
      }
    }

    const rowCa = _normalizeCaNumber(row.ca);
    const itemCa = _purchaseItemCa(item);
    if (rowCa && itemCa) {
      if (rowCa === itemCa) {
        matches.push('CA');
      } else {
        blocked = true;
        blockReason = `CA divergente (arquivo ${row.ca}, item ${item.epi_ca || item.ca})`;
        divergences.push(blockReason);
      }
    } else if (!rowCa) {
      divergences.push('CA ausente no arquivo');
    } else {
      divergences.push('CA ausente no item da requisição');
    }

    const itemName = item.epi_name || item.epi_display_name;
    const description = _purchaseTextRelation(row.epi, itemName);
    if (description === 'equal') {
      matches.push('descrição');
    } else if (description === 'partial') {
      divergences.push(`descrição só parcialmente igual (arquivo "${row.epi}", item "${itemName}")`);
    } else if (description === 'different') {
      const message = `descrição diferente (arquivo "${row.epi}", item "${itemName}")`;
      divergences.push(message);
      contradictions.push(message);
    }

    const itemManufacturer = item.manufacturer || item.epi_manufacturer;
    const manufacturer = _purchaseTextRelation(row.fabricante, itemManufacturer);
    if (manufacturer === 'equal' || manufacturer === 'partial') {
      matches.push('fabricante');
    } else if (manufacturer === 'different') {
      const message = `fabricante diferente (arquivo "${row.fabricante}", item "${itemManufacturer}")`;
      divergences.push(message);
      contradictions.push(message);
    }

    const itemModel = item.epi_model_reference || item.model_reference;
    const model = _purchaseTextRelation(row.modelo, itemModel);
    if (model === 'equal') {
      matches.push('modelo');
    } else if (model === 'partial' || model === 'different') {
      const message = `modelo diferente (arquivo "${row.modelo}", item "${itemModel}")`;
      divergences.push(message);
      contradictions.push(message);
    }

    [['tamanho', 'size', 'tamanho'], ['tamanho_luva', 'glove_size', 'tamanho de luva'], ['tamanho_uniforme', 'uniform_size', 'tamanho de uniforme']]
      .forEach(([rowKey, itemKey, label]) => {
        const rowSize = _normalizePurchaseSize(row[rowKey]);
        const itemSize = _normalizePurchaseSize(item[itemKey]);
        if (rowSize && itemSize) {
          if (rowSize === itemSize) {
            matches.push(label);
          } else {
            const message = `${label} diferente (arquivo ${row[rowKey]}, item ${item[itemKey]})`;
            divergences.push(message);
            contradictions.push(message);
          }
        }
      });

    // Identidade do produto: id do item, ou descrição/modelo IGUAIS. O CA
    // coincidente confirma, mas não identifica sozinho. Descrição parcial,
    // fabricante, fornecedor, origem e colaborador nunca bastam. Qualquer
    // contradição torna o item inelegível.
    const identified = matches.some((m) => ['id do item', 'descrição', 'modelo'].includes(m));
    const resembles = identified || matches.includes('CA') || description === 'partial' || matches.includes('fabricante');
    const eligible = !blocked && identified && contradictions.length === 0;
    const strong = eligible && matches.includes('CA')
      && matches.some((m) => ['descrição', 'modelo', 'id do item'].includes(m))
      && divergences.length === 0;
    return {
      itemId: item.id ?? item.purchase_request_item_id,
      item,
      eligible,
      blocked,
      blockReason,
      contradicted: contradictions.length > 0,
      relevant: resembles,
      strong: Boolean(strong),
      matches,
      divergences
    };
  }

  function evaluatePurchaseImportCandidates(rows, prItems) {
    const items = Array.isArray(prItems) ? prItems : [];
    const evaluated = (Array.isArray(rows) ? rows : []).map((row, rowIndex) => {
      const all = items.map((item) => _evaluatePurchaseImportCandidate(row, item));
      const candidates = all.filter((c) => c.relevant);
      const strong = candidates.filter((c) => c.strong);
      const caMissing = !_normalizeCaNumber(row.ca);
      const notes = [];
      if (caMissing) { notes.push('CA ausente: escolha e confirme o item manualmente.'); }
      if (!candidates.some((c) => c.eligible)) { notes.push('Nenhum item da requisição corresponde a esta linha.'); }
      if (strong.length > 1) { notes.push('Mais de um item corresponde a esta linha: escolha manualmente.'); }
      return {
        rowIndex,
        row,
        candidates,
        caMissing,
        suggestedItemId: !caMissing && strong.length === 1 ? strong[0].itemId : null,
        notes
      };
    });
    // A mesma sugestão para duas linhas é ambígua: nenhuma das duas é sugerida.
    const counts = new Map();
    evaluated.forEach((r) => { if (r.suggestedItemId != null) { counts.set(String(r.suggestedItemId), (counts.get(String(r.suggestedItemId)) || 0) + 1); } });
    evaluated.forEach((r) => {
      if (r.suggestedItemId != null && counts.get(String(r.suggestedItemId)) > 1) {
        r.suggestedItemId = null;
        r.notes.push('Outra linha também corresponde a este item: escolha manualmente.');
      }
    });
    return evaluated;
  }

  // Valida as escolhas do operador antes de enviar. `decisions` é um array
  // alinhado às linhas: id do item escolhido, 'ignore' ou vazio (pendente).
  function validatePurchaseImportDecisions(evaluation, decisions) {
    const errors = [];
    const chosen = new Map();
    (evaluation || []).forEach((r) => {
      const decision = decisions?.[r.rowIndex];
      const label = `Linha ${r.rowIndex + 1}`;
      if (decision === undefined || decision === null || decision === '') {
        errors.push(`${label}: escolha o item da requisição ou marque "não importar".`);
        return;
      }
      if (decision === 'ignore') { return; }
      const candidate = r.candidates.find((c) => String(c.itemId) === String(decision));
      if (!candidate) { errors.push(`${label}: o item escolhido não é candidato desta linha.`); return; }
      if (candidate.blocked) { errors.push(`${label}: ${candidate.blockReason}.`); return; }
      if (!candidate.eligible) {
        errors.push(candidate.contradicted
          ? `${label}: a linha contradiz o item #${candidate.itemId} (${candidate.divergences.join('; ')}).`
          : `${label}: o item escolhido não tem identificação inequívoca (CA, descrição ou modelo iguais, ou id do item).`);
        return;
      }
      const key = String(decision);
      if (chosen.has(key)) { errors.push(`${label}: o item #${key} já foi escolhido na linha ${chosen.get(key) + 1}.`); return; }
      chosen.set(key, r.rowIndex);
    });
    return errors;
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  // Os nomes globais são o contrato legado consumido por views/purchases.js
  // (`globalThis._matchPurchaseImportRows?.(...)` etc.) e antes vinham das
  // declarações de bloco do app.js. Atribuição direta (não condicional): este
  // módulo é a única definição.

  const purchaseImportExports = {
    _normalizeCa,
    _parsePurchaseMoney,
    _parsePurchaseQuantity,
    _normalizePurchaseText,
    _normalizePurchaseSize,
    _normalizePurchaseOrigin,
    _scorePurchaseImportMatch,
    _matchPurchaseImportRows,
    _normalizeCaNumber,
    evaluatePurchaseImportCandidates,
    validatePurchaseImportDecisions
  };

  for (const [name, fn] of Object.entries(purchaseImportExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_PURCHASES_BUSINESS__ = Object.freeze({ ...purchaseImportExports });
})();
