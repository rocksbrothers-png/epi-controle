"""Testes ESTRUTURAIS (LEGADOS) do ux-phase41.js — #343 PR1.

NATUREZA DESTES TESTES
Tudo aqui é verificação de TEXTO no arquivo: procura-se um símbolo, um nome de
função, um trecho. Nada neste módulo executa o phase41. Passar aqui significa
que o código está escrito de certa forma — NÃO que ele funciona, e nem sequer
que ele chega a iniciar.

POR QUE ISSO IMPORTA NESTE ARQUIVO
A caracterização comportamental da #343 PR1 mediu que o `ux-phase41.js` NÃO
inicializa em produção: o IIFE grava `__EPI_PHASE41_BOUND__` nas primeiras
linhas e, logo abaixo, pergunta ao `ensureModuleBound('phase41')` se já está
ligado — que deriva exatamente essa chave. O módulo retorna antes do gate da
flag. Esta suíte inteira estava verde durante todo esse tempo.

ONDE ESTÁ A PROVA DE COMPORTAMENTO
Em `static/js/test/run-tests.js`, seção PR1 (gates `PR1 C-*`), que carrega o
módulo na ordem servida e mede guarda de saída, leitura de flag e listeners.

NÃO APAGAR sem substituir: alguns destes asserts guardam decisões reais de
escopo (ver `test_phase41_uses_namespaced_storage_and_reset_query`).
"""


from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (_repo_root() / path).read_text(encoding="utf-8")


def test_legacy_structural_phase41_has_global_guard_and_iife():
    """LEGADO/ESTRUTURAL. Caracteriza o estado atual, não o desejado.

    ATENÇÃO — a segunda asserção deste teste EXIGE a presença da linha que
    torna o módulo inerte. `ensureModuleBound('phase41')` deriva o nome
    `__EPI_PHASE41_BOUND__`; o IIFE grava esse mesmo global duas linhas antes e
    recebe de si mesmo a resposta "já ligado". Enquanto a colisão existir, este
    assert a documenta. Quando ela for corrigida, este teste DEVE falhar — é o
    sinal de que a correção chegou, e o momento de removê-lo.

    Não transformar em asserção "o defeito precisa continuar existindo" sem
    este comentário. Ver `PR1 C-1` em static/js/test/run-tests.js.
    """
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
