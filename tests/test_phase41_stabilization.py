from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (_repo_root() / path).read_text(encoding="utf-8")


def test_phase41_has_global_guard_and_iife():
    content = _read("static/ux-phase41.js")
    assert "(function phase41Iife()" in content
    assert "__EPI_PHASE41_BOUND__" in content


def test_phase41_uses_namespaced_storage_and_reset_query():
    """Revisado na #343 F5-B.

    A chave de ROLAGEM (`epi:ux:phase41:scroll:v2`) saiu: posição de rolagem é
    estado de navegação, e o contrato agora manda reentrar no módulo pelo topo.
    Ela era, aliás, escrita e nunca lida — persistia navegação sem sequer
    entregar a função.

    A chave de CONTEXTO (`epi:ux:phase41:context:v2`) continua aqui de
    propósito: rascunho de formulário é outra categoria e sai na F5-C, com
    contrato próprio. Se alguém antecipar, este gate cai — e a decisão volta a
    ser explícita.
    """
    content = _read("static/ux-phase41.js")
    assert "epi:ux:phase41:context:v2" in content
    assert "ux_phase41_reset" in content
    corpo = "\n".join(
        linha for linha in content.split("\n")
        if not linha.strip().startswith("//")
    )
    # A chave pode ser NOMEADA, mas só para ser apagada: remover o gravador não
    # apaga o que já está no disco de quem rodou a versão anterior, e o
    # encerramento de sessão preserva `localStorage` de propósito (F2).
    for linha in corpo.split("\n"):
        if "epi:ux:phase41:scroll:v2" in linha:
            assert "removeItem" in linha, (
                f"a persistência de rolagem voltou (#343 F5-B): {linha.strip()[:70]}"
            )
    assert "removerChaveLegadaDeRolagem" in corpo, (
        "a limpeza da chave legada de rolagem sumiu: ela ficaria no disco para sempre"
    )


def test_phase41_blocks_sensitive_field_persistence():
    content = _read("static/ux-phase41.js")
    assert "SENSITIVE_FIELD_PATTERN" in content
    assert "shouldPersistField" in content
    for token in ["password", "token", "cpf", "signature", "qr", "secret"]:
        assert token in content


def test_phase41_has_safe_enter_guards_for_critical_forms():
    content = _read("static/ux-phase41.js")
    assert "CRITICAL_FORMS" in content
    assert "delivery-form" in content
    assert "resolveSafePrimaryAction" in content
    assert "hasAutocompleteContext" in content


def test_phase41_has_loading_failsafe_and_overlay_close_controls():
    content = _read("static/ux-phase41.js")
    assert "startPendingFailsafe" in content
    assert "setTimeout(function ()" in content
    assert "closeUiOverlays({ includeModal: true })" in content
    assert "closeUiOverlays({ includeModal: false })" in content
