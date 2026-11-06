'use strict';
/* global tr, escapeHtml, formatDateTime, canAccessCommercialArea, requirePermission --
   globais do app.js, de shared/*, de views/view-helpers.js, de modules/auth e da C1, resolvidos na chamada */

// Interface: contrato comercial (UBX Comercial, fatia C3 — extraída de static/app.js).
//
// As 14 funções do painel do contrato comercial na tela Comercial: situação do
// contrato com binding vivo do idioma, preenchimento e limpeza dos campos de
// contratante, prestador, cláusulas, assinatura e e-mail, montagem do corpo do
// contrato a partir do formulário, e as ações (ler, salvar rascunho, gerar,
// assinar, enviar o PDF assinado, registrar o envio por e-mail, abrir o PDF e
// abrir/baixar o arquivo gerado). A "assinatura" aqui é a do contrato
// comercial; nada tem a ver com a assinatura eletrônica das fichas de EPI.
//
// Corpos idênticos aos do app.js (mesmas chaves de tradução, fallbacks, escapes,
// ids, classes e ordem das operações); a única linha nova em cada função é a
// leitura de `state` e `refs`, que no app.js eram constantes do bloco de carga e
// aqui vêm de globalThis.__EPI_APP_STATE__ e globalThis.__EPI_REFS__ (os MESMOS
// objetos, publicados pelo app.js; nenhum estado paralelo). HTTP só pela C2
// (../integrations/commercial-api.js) e pelo updateCompany de Empresas; nenhuma
// chamada direta a `api`. Autorização (commercial:view, Administrador Master,
// escopo da empresa) segue no backend: as checagens daqui só escondem ou evitam
// ações, como antes.
//
// Publicação: as 7 síncronas eram globais do app.js (Annex B) e continuam em
// globalThis com os mesmos nomes; as 7 assíncronas (`async function` de bloco,
// nunca globais) ficam só no namespace congelado __EPI_COMMERCIAL_CONTRACT_VIEW__,
// e todas entram na fachada __EPI_COMMERCIAL_VIEW__ (./commercial-view.js, que
// carrega depois deste). Carga idempotente.
(function () {
  if (globalThis.__EPI_MODULE_COMMERCIAL_CONTRACT_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMMERCIAL_CONTRACT_VIEW_LOADED__ = true;

  function contractStatusLabel(status) {
    const labels = {
      draft: 'Rascunho',
      generated: 'Gerado',
      sent: 'Enviado',
      pending_signature: 'Pendente de assinatura',
      signed: 'Assinado',
      active: 'Ativo',
      closed: 'Encerrado',
      archived: 'Arquivado'
    };
    const code = String(status || '').toLowerCase() || 'draft';
    // Código desconhecido continua visível como veio do backend.
    return labels[code] ? tr(`commercial.contractStatusLabels.${code}`, labels[code]) : status;
  }

  function renderCommercialContractPanel() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const contract = state.commercialContract;
    if (!contract) return;
    if (refs.commercialContractStatus) {
      const code = String(contract.status || '').toLowerCase() || 'draft';
      // Binding vivo: a troca de idioma retraduz o rótulo sem reler o contrato nem tocar no formulário.
      refs.commercialContractStatus.textContent = globalThis.EpiI18n?.textFor?.(refs.commercialContractStatus, 'commercial.panel.contractStatus', 'Status do contrato: {status}', { status: contractStatusLabel(contract.status) }, { status: `commercial.contractStatusLabels.${code}` })
        ?? tr('commercial.panel.contractStatus', 'Status do contrato: {status}', { status: contractStatusLabel(contract.status) });
    }
    if (refs.commercialContractNumber) refs.commercialContractNumber.value = contract.contract_number || '';
    if (refs.commercialContractIssueDate) refs.commercialContractIssueDate.value = contract.issue_date || '';
    if (refs.commercialContractorAddress) refs.commercialContractorAddress.value = contract.contractor_address || '';
    if (refs.commercialContractorRepresentative) refs.commercialContractorRepresentative.value = contract.contractor_representative || '';
    if (refs.commercialContractorRole) refs.commercialContractorRole.value = contract.contractor_representative_role || '';
    if (refs.commercialContractorEmail) refs.commercialContractorEmail.value = contract.contractor_email || '';
    if (refs.commercialContractorPhone) refs.commercialContractorPhone.value = contract.contractor_phone || '';
    if (refs.commercialContractorW1) refs.commercialContractorW1.value = contract.contractor_witness_1 || '';
    if (refs.commercialContractorW2) refs.commercialContractorW2.value = contract.contractor_witness_2 || '';
    if (refs.commercialProviderName) refs.commercialProviderName.value = contract.provider_name || '';
    if (refs.commercialProviderLegalName) refs.commercialProviderLegalName.value = contract.provider_legal_name || '';
    if (refs.commercialProviderCnpj) refs.commercialProviderCnpj.value = contract.provider_cnpj || '';
    if (refs.commercialProviderAddress) refs.commercialProviderAddress.value = contract.provider_address || '';
    if (refs.commercialProviderRepresentative) refs.commercialProviderRepresentative.value = contract.provider_representative || '';
    if (refs.commercialProviderRole) refs.commercialProviderRole.value = contract.provider_representative_role || '';
    if (refs.commercialProviderEmail) refs.commercialProviderEmail.value = contract.provider_email || '';
    if (refs.commercialProviderPhone) refs.commercialProviderPhone.value = contract.provider_phone || '';
    if (refs.commercialProviderWitnesses) refs.commercialProviderWitnesses.value = contract.provider_witnesses || '';
    if (refs.commercialContractClauses) {
      const clausesValue = contract.clauses_text || state.commercialClauseTemplate || refs.commercialContractClauses.value || '';
      refs.commercialContractClauses.value = clausesValue;
      state.commercialClauseTemplate = clausesValue;
    }
    if (refs.commercialEmailTo) refs.commercialEmailTo.value = contract.last_email_to || contract.contractor_email || '';
    if (refs.commercialEmailSubject) refs.commercialEmailSubject.value = contract.last_email_subject || 'Contrato comercial EPI Controle';
    if (refs.commercialEmailBody) refs.commercialEmailBody.value = contract.last_email_body || 'Segue contrato comercial para análise e assinatura.';
    if (refs.commercialContractEvents) {
      refs.commercialContractEvents.innerHTML = (contract.events || []).map((event) => `<div class="summary-item"><strong>${escapeHtml(event.event_type)}</strong><div>${formatDateTime(event.created_at)}</div></div>`).join('') || `<div class="summary-item">${escapeHtml(tr('commercial.panel.noContractHistory', 'Sem histórico de contrato.'))}</div>`;
    }
  }

  function resetCommercialContractForm({ preserveClauses = true } = {}) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const clauses = preserveClauses ? (refs.commercialContractClauses?.value || state.commercialClauseTemplate || '') : '';
    if (refs.commercialContractStatus) {
      refs.commercialContractStatus.textContent = globalThis.EpiI18n?.textFor?.(refs.commercialContractStatus, 'commercial.panel.contractStatus', 'Status do contrato: {status}', { status: contractStatusLabel('draft') }, { status: 'commercial.contractStatusLabels.draft' })
        ?? tr('commercial.panel.contractStatus', 'Status do contrato: {status}', { status: contractStatusLabel('draft') });
    }
    if (refs.commercialContractNumber) refs.commercialContractNumber.value = '';
    if (refs.commercialContractIssueDate) refs.commercialContractIssueDate.value = '';
    if (refs.commercialContractorAddress) refs.commercialContractorAddress.value = '';
    if (refs.commercialContractorRepresentative) refs.commercialContractorRepresentative.value = '';
    if (refs.commercialContractorRole) refs.commercialContractorRole.value = '';
    if (refs.commercialContractorEmail) refs.commercialContractorEmail.value = '';
    if (refs.commercialContractorPhone) refs.commercialContractorPhone.value = '';
    if (refs.commercialContractorW1) refs.commercialContractorW1.value = '';
    if (refs.commercialContractorW2) refs.commercialContractorW2.value = '';
    if (refs.commercialProviderName) refs.commercialProviderName.value = '';
    if (refs.commercialProviderLegalName) refs.commercialProviderLegalName.value = '';
    if (refs.commercialProviderCnpj) refs.commercialProviderCnpj.value = '';
    if (refs.commercialProviderAddress) refs.commercialProviderAddress.value = '';
    if (refs.commercialProviderRepresentative) refs.commercialProviderRepresentative.value = '';
    if (refs.commercialProviderRole) refs.commercialProviderRole.value = '';
    if (refs.commercialProviderEmail) refs.commercialProviderEmail.value = '';
    if (refs.commercialProviderPhone) refs.commercialProviderPhone.value = '';
    if (refs.commercialProviderWitnesses) refs.commercialProviderWitnesses.value = '';
    if (refs.commercialContractClauses) refs.commercialContractClauses.value = clauses;
    if (refs.commercialSignatureName) refs.commercialSignatureName.value = '';
    if (refs.commercialSignatureData) refs.commercialSignatureData.value = '';
    if (refs.commercialEmailTo) refs.commercialEmailTo.value = '';
    if (refs.commercialEmailSubject) refs.commercialEmailSubject.value = 'Contrato comercial EPI Controle';
    if (refs.commercialEmailBody) refs.commercialEmailBody.value = 'Segue contrato comercial para análise e assinatura.';
    if (refs.commercialSignedFile) refs.commercialSignedFile.value = '';
    if (refs.commercialContractEvents) refs.commercialContractEvents.innerHTML = `<div class="summary-item">${escapeHtml(tr('commercial.panel.noContractHistory', 'Sem histórico de contrato.'))}</div>`;
    state.commercialContract = null;
    state.commercialClauseTemplate = clauses;
  }

  async function loadCommercialContract(companyId) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!companyId || !refs.commercialForm || !canAccessCommercialArea()) return;
    try {
      const payload = await globalThis.__EPI_COMMERCIAL_API__.getContract(state.user.id, companyId);
      state.commercialContract = payload.contract || null;
      renderCommercialContractPanel();
    } catch (error) {
      if (error?.status === 403) {
        resetCommercialContractForm({ preserveClauses: true });
        return;
      }
      console.warn('[commercial-contract] Não foi possível carregar contrato', error);
    }
  }

  function buildCommercialContractPayload() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const companyId = refs.commercialCompany?.value;
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    return {
      actor_user_id: state.user.id,
      company_id: Number(companyId || 0),
      contract_number: refs.commercialContractNumber?.value || '',
      issue_date: refs.commercialContractIssueDate?.value || '',
      start_date: refs.commercialForm?.elements.contract_start?.value || company?.contract_start || '',
      end_date: refs.commercialForm?.elements.contract_end?.value || company?.contract_end || '',
      status: state.commercialContract?.status || 'draft',
      contractor_name: company?.name || '',
      contractor_legal_name: company?.legal_name || '',
      contractor_trade_name: company?.name || '',
      contractor_cnpj: company?.cnpj || '',
      contractor_address: refs.commercialContractorAddress?.value || '',
      contractor_representative: refs.commercialContractorRepresentative?.value || '',
      contractor_representative_role: refs.commercialContractorRole?.value || '',
      contractor_email: refs.commercialContractorEmail?.value || '',
      contractor_phone: refs.commercialContractorPhone?.value || '',
      contractor_witness_1: refs.commercialContractorW1?.value || '',
      contractor_witness_2: refs.commercialContractorW2?.value || '',
      provider_name: refs.commercialProviderName?.value || '',
      provider_legal_name: refs.commercialProviderLegalName?.value || '',
      provider_cnpj: refs.commercialProviderCnpj?.value || '',
      provider_address: refs.commercialProviderAddress?.value || '',
      provider_representative: refs.commercialProviderRepresentative?.value || '',
      provider_representative_role: refs.commercialProviderRole?.value || '',
      provider_email: refs.commercialProviderEmail?.value || '',
      provider_phone: refs.commercialProviderPhone?.value || '',
      provider_witnesses: refs.commercialProviderWitnesses?.value || '',
      clauses_text: refs.commercialContractClauses?.value || '',
      notes: refs.commercialForm?.elements.commercial_notes?.value || ''
    };
  }

  function downloadCommercialContractPdf() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const companyId = refs.commercialCompany?.value;
    if (!companyId) return;
    globalThis.open(globalThis.__EPI_COMMERCIAL_API__.contractPdfUrl({ actor_user_id: state.user.id, company_id: companyId }), '_blank');
  }

  async function saveCommercialContractDraft(showToast = false) {
    const state = globalThis.__EPI_APP_STATE__;
    const payload = buildCommercialContractPayload();
    if (!payload.company_id) return;
    const response = await globalThis.__EPI_COMMERCIAL_API__.saveContractDraft(payload);
    state.commercialContract = response.contract || null;
    renderCommercialContractPanel();
    if (showToast) alert(tr('commercial.panel.draftSaved', 'Contrato salvo em rascunho.'));
  }

  async function generateCommercialContract() {
    const state = globalThis.__EPI_APP_STATE__;
    try {
      const payload = buildCommercialContractPayload();
      const response = await globalThis.__EPI_COMMERCIAL_API__.generateContract(payload);
      state.commercialContract = response.contract || null;
      renderCommercialContractPanel();
      alert(tr('commercial.panel.generated', 'Contrato gerado com sucesso.'));
    } catch (error) { alert(error.message); }
  }

  function viewGeneratedCommercialContract() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const companyId = refs.commercialCompany?.value;
    if (!companyId) return;
    globalThis.open(globalThis.__EPI_COMMERCIAL_API__.contractPdfUrl({ actor_user_id: state.user.id, company_id: companyId }), '_blank');
  }

  function downloadGeneratedCommercialContract() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const companyId = refs.commercialCompany?.value;
    if (!companyId) return;
    globalThis.open(globalThis.__EPI_COMMERCIAL_API__.contractFileUrl({ actor_user_id: state.user.id, company_id: companyId, kind: 'generated' }), '_blank');
  }

  async function signCommercialContractAction() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    try {
      const companyId = refs.commercialCompany?.value;
      const signatureName = refs.commercialSignatureName?.value || '';
      const signatureData = refs.commercialSignatureData?.value || '';
      const response = await globalThis.__EPI_COMMERCIAL_API__.signContract({ actor_user_id: state.user.id, company_id: Number(companyId || 0), signature_name: signatureName, signature_data: signatureData });
      state.commercialContract = response.contract || null;
      renderCommercialContractPanel();
      alert(tr('commercial.panel.signatureRecorded', 'Assinatura digital registrada.'));
    } catch (error) { alert(error.message); }
  }

  async function uploadSignedCommercialContract() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    try {
      const file = refs.commercialSignedFile?.files?.[0];
      if (!file) return alert(tr('commercial.panel.selectSignedPdf', 'Selecione um PDF assinado.'));
      const companyId = refs.commercialCompany?.value;
      const fileBase64 = await fileToBase64(file);
      const response = await globalThis.__EPI_COMMERCIAL_API__.uploadSignedContract({
        actor_user_id: state.user.id,
        company_id: Number(companyId || 0),
        file_name: file.name,
        file_mime: file.type || 'application/pdf',
        file_base64: fileBase64
      });
      state.commercialContract = response.contract || null;
      renderCommercialContractPanel();
      alert(tr('commercial.panel.signedUploaded', 'Contrato assinado enviado com sucesso.'));
    } catch (error) { alert(error.message); }
  }

  async function sendCommercialContractByEmail() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    try {
      const companyId = refs.commercialCompany?.value;
      const response = await globalThis.__EPI_COMMERCIAL_API__.sendContractEmail({
        actor_user_id: state.user.id,
        company_id: Number(companyId || 0),
        email_to: refs.commercialEmailTo?.value || '',
        subject: refs.commercialEmailSubject?.value || '',
        body: refs.commercialEmailBody?.value || ''
      });
      state.commercialContract = response.contract || null;
      renderCommercialContractPanel();
      alert(tr('commercial.panel.emailLogged', 'Registro de envio por e-mail atualizado.'));
    } catch (error) { alert(error.message); }
  }

  async function saveCommercialContractManagement() {
    if (!requirePermission('commercial:view')) return;
    try {
      await saveCommercialContractDraft(true);
    } catch (error) {
      alert(error.message);
    }
  }

  const exportsMap = {
    contractStatusLabel,
    renderCommercialContractPanel,
    resetCommercialContractForm,
    loadCommercialContract,
    buildCommercialContractPayload,
    downloadCommercialContractPdf,
    saveCommercialContractDraft,
    generateCommercialContract,
    viewGeneratedCommercialContract,
    downloadGeneratedCommercialContract,
    signCommercialContractAction,
    uploadSignedCommercialContract,
    sendCommercialContractByEmail,
    saveCommercialContractManagement
  };

  // Só as síncronas eram globais no app.js; as assíncronas seguem fora de globalThis.
  for (const name of [
    'contractStatusLabel',
    'renderCommercialContractPanel',
    'resetCommercialContractForm',
    'buildCommercialContractPayload',
    'downloadCommercialContractPdf',
    'viewGeneratedCommercialContract',
    'downloadGeneratedCommercialContract'
  ]) {
    globalThis[name] = exportsMap[name];
  }
  globalThis.__EPI_COMMERCIAL_CONTRACT_VIEW__ = Object.freeze({ ...exportsMap });
})();
