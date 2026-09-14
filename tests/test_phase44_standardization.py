import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase44_guard_flag_and_classic_fallback_are_present():
    content = _read('static/ux-phase44.js')
    assert '__EPI_PHASE44_BOUND__' in content
    assert "getFeatureFlag('ux_phase44_enabled'" in content
    assert 'if (!isEnabled()) {' in content
    assert 'fluxo clássico mantido' in content


def test_phase44_reusable_helpers_and_hardening_contract_present():
    content = _read('static/ux-phase44.js')
    assert 'function createDropdown(root)' in content
    assert 'function createActionBar(options)' in content
    assert 'function createConfirmInline(button, options)' in content
    assert 'function createBadge(label, tone)' in content
    assert 'safeOn(target, eventName, handler, options)' in content
    assert 'try {' in content and 'catch (error)' in content
    assert '__EPI_PHASE44_FETCH_BRIDGED__' in content


def test_phase44_script_and_flag_registration_available_in_app_bootstrap():
    app_js = _read('static/app.js')
    assert "uxPhase44Enabled: 'ux_phase44_enabled'" in app_js
    assert "ux_phase44_enabled: { queryParam: 'ux_phase44'" in app_js
    assert re.search(r"phase44Script\.src = '/ux-phase44\.js\?v=[^']+'", app_js)


def test_phase44_critical_actions_support_explicit_attributes_with_text_fallback():
    content = _read('static/ux-phase44.js')
    assert "button.dataset.confirmAction === 'true'" in content
    assert "button.dataset.criticalAction === 'true'" in content
    assert "button.dataset.confirmMessage" in content
    assert "var fallbackTextMatch = /excluir|remover|inativar|desativar/.test(text);" in content


def test_phase44_feedback_avoids_timeout_success_and_uses_real_signals():
    content = _read('static/ux-phase44.js')
    assert "setScreenStatus(viewName, 'Ação enviada', 'loading');" in content
    assert 'htmx:afterRequest' in content and 'Sucesso confirmado.' in content
    assert "document.dispatchEvent(new CustomEvent(response && response.ok ? 'epi:action-success' : 'epi:action-error'" in content
    assert 'Ação concluída com sucesso.' not in content


def test_phase44_nao_persiste_mais_filtro_e_limpa_o_legado():
    """Revisado na #343 F5-B — antes exigia a persistência do filtro.

    Filtro é estado de NAVEGAÇÃO: reentrar no módulo mostra a lista sem filtro,
    inclusive para o mesmo usuário. Saíram o prefixo de storage, o
    `persistContext`/`restoreContext` e os helpers de escrita.

    O namespace ficou — e só ele — porque `removePhase44Storage()` agora roda
    INCONDICIONALMENTE no init, para apagar as chaves que versões anteriores
    gravaram no navegador de quem já usou o sistema.
    """
    content = _read('static/ux-phase44.js')
    corpo = "\n".join(
        linha for linha in content.split("\n")
        if not linha.strip().startswith("//")
    )
    assert "STORAGE_NAMESPACE = 'epi.ux.phase44'" in corpo
    assert 'removePhase44Storage();' in corpo, 'a limpeza das chaves legadas sumiu'
    for proibido in ('STORAGE_FILTER_PREFIX', 'restoreContext', 'persistContext',
                     'safeLocalStorageSet', "ux_phase44_reset"):
        assert proibido not in corpo, f'{proibido} voltou ao phase44: ver #343 F5-B'
    assert 'SENSITIVE_FIELD_PATTERN' in corpo
