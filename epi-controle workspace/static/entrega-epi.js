(function entregaEpiInteractiveIife() {
  if (globalThis.__EPI_ENTREGA_EPI_BOUND__) return;
  globalThis.__EPI_ENTREGA_EPI_BOUND__ = true;

  function safeOn(target, eventName, handler, options) {
    try {
      if (typeof globalThis.safeOn === 'function') return globalThis.safeOn(target, eventName, handler, options);
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (error) {
      console.warn('[entrega-epi] safeOn falhou', error);
      return false;
    }
  }

  function isInteractiveEnabled() {
    try {
      if (typeof globalThis.getFeatureFlag === 'function') {
        return globalThis.getFeatureFlag('entrega_epi_htmx_enabled', { defaultValue: false }) === true;
      }
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_entrega_epi') === '1') return true;
      if (params.get('ux_entrega_epi') === '0') return false;
      return globalThis.localStorage?.getItem('entrega_epi_htmx_enabled') === '1';
    } catch (error) {
      console.warn('[entrega-epi] fallback de flag', error);
      return false;
    }
  }

  function byId(id) { return document.getElementById(id); }

  function init() {
    try {
      if (!isInteractiveEnabled()) return;
      var form = byId('delivery-form');
      if (!form) return;

      var guide = byId('delivery-ux-guide');
      var stepsWrap = byId('delivery-ux-steps');
      var feedback = byId('delivery-ux-feedback');
      var loading = byId('delivery-ux-loading');
      var reviewBox = byId('delivery-ux-review');
      var stepTitle = byId('delivery-ux-step-title');
      var stepHelper = byId('delivery-ux-step-helper');
      var backBtn = byId('delivery-ux-back');
      var clearBtn = byId('delivery-ux-clear');
      var submitBtn = form.querySelector('button[type="submit"]');

      var employeeField = byId('delivery-employee');
      var employeeSearch = byId('delivery-employee-search');
      var epiField = byId('delivery-epi');
      var epiSearch = byId('delivery-epi-search');
      var companyField = byId('delivery-company');
      var unitField = byId('delivery-unit-filter');
      var dateField = form.elements.delivery_date;
      var nextField = byId('delivery-next-replacement');
      var qtyField = form.elements.quantity;
      var qrCodeField = byId('delivery-stock-item-code');

      if (!guide || !stepsWrap || !feedback || !submitBtn) return;
      guide.hidden = false;

      var step = 1;
      var searchDropdowns = [];
      var watchedFields = [employeeField, epiField, qtyField, dateField, nextField, qrCodeField].filter(Boolean);

      function setLoading(value, text) {
        if (!loading) return;
        loading.hidden = !value;
        loading.textContent = text || 'Atualizando dados...';
      }

      function setFeedback(message, tone) {
        if (!feedback) return;
        feedback.textContent = String(message || '');
        feedback.classList.remove('is-error', 'is-success');
        if (tone === 'error') feedback.classList.add('is-error');
        if (tone === 'success') feedback.classList.add('is-success');
      }

      function markRequired() {
        watchedFields.forEach(function (field) {
          var required = field?.required || field?.id === 'delivery-stock-item-code';
          if (!required) return;
          var empty = !String(field.value || '').trim();
          field.classList.toggle('delivery-ux-required-missing', empty && step >= 3);
        });
      }

      function updateStepsUi() {
        var items = Array.from(stepsWrap.querySelectorAll('[data-step]'));
        items.forEach(function (item) {
          var itemStep = Number(item.getAttribute('data-step') || 0);
          item.classList.toggle('is-active', itemStep === step);
          item.classList.toggle('is-done', itemStep < step);
        });

        if (step === 1) {
          stepTitle.textContent = 'Etapa 1: selecionar colaborador';
          stepHelper.textContent = 'Use busca rápida ou selecione diretamente na lista.';
          submitBtn.textContent = 'Ir para seleção de EPI';
          submitBtn.type = 'button';
          reviewBox.hidden = true;
        } else if (step === 2) {
          stepTitle.textContent = 'Etapa 2: selecionar EPI';
          stepHelper.textContent = 'Filtre por nome e fabricante para acelerar.';
          submitBtn.textContent = 'Ir para revisão';
          submitBtn.type = 'button';
          reviewBox.hidden = true;
        } else if (step === 3) {
          stepTitle.textContent = 'Etapa 3: conferir dados';
          stepHelper.textContent = 'Revise colaborador, EPI e datas antes de confirmar.';
          submitBtn.textContent = 'Ir para confirmação';
          submitBtn.type = 'button';
          reviewBox.hidden = false;
          renderReview();
        } else {
          stepTitle.textContent = 'Etapa 4: confirmar entrega';
          stepHelper.textContent = 'Nenhuma informação será salva sem esta confirmação.';
          submitBtn.textContent = 'Confirmar entrega';
          submitBtn.type = 'submit';
          reviewBox.hidden = false;
          renderReview();
        }
        markRequired();
      }

      function selectedText(selectField) {
        var option = selectField?.selectedOptions?.[0];
        return String(option?.textContent || '').trim() || '-';
      }

      function renderReview() {
        if (!reviewBox) return;
        reviewBox.innerHTML = [
          '<strong>Resumo da entrega</strong>',
          '<div>Empresa: ' + selectedText(companyField) + '</div>',
          '<div>Unidade: ' + selectedText(unitField) + '</div>',
          '<div>Colaborador: ' + selectedText(employeeField) + '</div>',
          '<div>EPI: ' + selectedText(epiField) + '</div>',
          '<div>Qtd: ' + (qtyField?.value || '1') + '</div>',
          '<div>Data entrega: ' + (dateField?.value || '-') + '</div>',
          '<div>Próxima troca: ' + (nextField?.value || '-') + '</div>',
          '<div>Código lido: ' + (qrCodeField?.value || 'pendente') + '</div>'
        ].join('');
      }

      function canAdvanceTo(nextStep) {
        if (nextStep <= 1) return true;
        if (nextStep >= 2 && !String(employeeField?.value || '').trim()) {
          setFeedback('Selecione um colaborador para avançar.', 'error');
          return false;
        }
        if (nextStep >= 3 && !String(epiField?.value || '').trim()) {
          setFeedback('Selecione um EPI para avançar.', 'error');
          return false;
        }
        if (nextStep >= 4) {
          var missing = watchedFields.some(function (field) {
            var required = field?.required || field?.id === 'delivery-stock-item-code';
            return required && !String(field.value || '').trim();
          });
          if (missing) {
            setFeedback('Preencha os campos obrigatórios destacados antes de confirmar.', 'error');
            return false;
          }
        }
        setFeedback('Etapa validada com sucesso.', 'success');
        return true;
      }

      function setStep(nextStep) {
        step = Math.max(1, Math.min(4, Number(nextStep || 1)));
        updateStepsUi();
      }

      function clearSelections() {
        if (employeeSearch) employeeSearch.value = '';
        if (epiSearch) epiSearch.value = '';
        if (employeeField) employeeField.value = '';
        if (epiField) epiField.value = '';
        if (qrCodeField) qrCodeField.value = '';
        setStep(1);
        setFeedback('Seleções limpas. Fluxo reiniciado.', '');
        watchedFields.forEach(function (field) { field?.dispatchEvent(new Event('change', { bubbles: true })); });
      }

      function mountSearchDropdown(input, selectField, emptyText) {
        if (!input || !selectField) return;
        input.parentElement?.classList.add('delivery-ux-search-box');
        var dropdown = document.createElement('div');
        dropdown.className = 'delivery-ux-dropdown';
        input.parentElement?.appendChild(dropdown);
        searchDropdowns.push(dropdown);

        function close() { dropdown.classList.remove('open'); }
        function open() { dropdown.classList.add('open'); }

        function render() {
          var term = String(input.value || '').toLowerCase().trim();
          var options = Array.from(selectField.options || [])
            .filter(function (option) { return String(option.value || '').trim(); })
            .filter(function (option) { return !term || String(option.textContent || '').toLowerCase().includes(term); })
            .slice(0, 8);
          if (!options.length) {
            dropdown.innerHTML = '<button type="button" class="ghost" data-empty="1">' + emptyText + '</button>';
            open();
            return;
          }
          dropdown.innerHTML = options.map(function (option) {
            return '<button type="button" data-value="' + String(option.value) + '">' + String(option.textContent || '') + '</button>';
          }).join('');
          open();
        }

        safeOn(input, 'focus', render);
        safeOn(input, 'input', render);
        safeOn(dropdown, 'click', function (event) {
          var btn = event.target.closest('button[data-value]');
          if (!btn) return;
          selectField.value = btn.getAttribute('data-value') || '';
          input.value = String(btn.textContent || '');
          close();
          selectField.dispatchEvent(new Event('change', { bubbles: true }));
          setFeedback('Seleção atualizada sem recarregar a página.', 'success');
        });
      }

      function closeAllDropdowns() {
        searchDropdowns.forEach(function (box) { box.classList.remove('open'); });
      }

      mountSearchDropdown(employeeSearch, employeeField, 'Nenhum colaborador encontrado para este filtro.');
      mountSearchDropdown(epiSearch, epiField, 'Nenhum EPI encontrado para este filtro.');

      safeOn(document, 'keydown', function (event) {
        if (event.key === 'Escape') closeAllDropdowns();
      });
      safeOn(document, 'click', function (event) {
        var inside = event.target.closest('.delivery-ux-search-box, .delivery-ux-dropdown');
        if (!inside) closeAllDropdowns();
      });

      safeOn(companyField, 'change', function () {
        setLoading(true, 'Carregando colaboradores e EPIs por empresa...');
        setTimeout(function () { setLoading(false); }, 280);
      });
      safeOn(unitField, 'change', function () {
        setLoading(true, 'Atualizando filtros por unidade...');
        setTimeout(function () { setLoading(false); }, 260);
      });

      safeOn(backBtn, 'click', function () {
        setStep(step - 1);
        setFeedback('Etapa anterior carregada.', '');
      });
      safeOn(clearBtn, 'click', clearSelections);

      watchedFields.forEach(function (field) {
        safeOn(field, 'change', function () {
          if (step >= 3) renderReview();
          markRequired();
        });
      });

      safeOn(submitBtn, 'click', function (event) {
        if (submitBtn.type === 'submit') return;
        event.preventDefault();
        var targetStep = step + 1;
        if (!canAdvanceTo(targetStep)) {
          markRequired();
          return;
        }
        setStep(targetStep);
      });

      safeOn(form, 'submit', function (event) {
        if (step < 4) {
          event.preventDefault();
          if (canAdvanceTo(step + 1)) setStep(step + 1);
          return;
        }
        setFeedback('Confirmando entrega... aguarde.', 'success');
      }, true);

      setFeedback('Fluxo interativo ativo. O modo clássico permanece disponível via flag OFF.', 'success');
      updateStepsUi();
    } catch (error) {
      console.error('[entrega-epi] Falha ao ativar fluxo guiado. Mantendo fluxo clássico.', error);
    }
  }

  if (document.readyState === 'loading') safeOn(document, 'DOMContentLoaded', init, { once: true });
  else init();
})();
