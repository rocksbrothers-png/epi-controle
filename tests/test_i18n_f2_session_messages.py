"""I18N-FULL-V1 — avisos de encerramento de sessão (F2) traduzidos SÓ na exibição.

Equivalência com o contrato F2 (tests/test_343_f2_teardown_logout.py):
- os textos canônicos continuam sendo gravados por `terminateSession('<texto>')`;
- `consumePendingSessionMessage` apaga a chave ANTES de exibir e só então traduz;
- o mapa de exibição cobre exatamente os avisos de MENSAGENS_DE_ENCERRAMENTO;
- em pt-BR o texto exibido é idêntico ao canônico (nenhuma mudança visível);
- nos outros 4 idiomas há tradução própria, sem placeholders.
"""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']


def _f2():
    spec = importlib.util.spec_from_file_location('f2', ROOT / 'tests' / 'test_343_f2_teardown_logout.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _consume_body():
    return _f2()._corpo_de(APP, 'consumePendingSessionMessage')


def _display_map():
    body = _consume_body()
    block = body[body.index('const avisosCanonicos = {'):body.index('};', body.index('const avisosCanonicos = {'))]
    return dict(re.findall(r"'([^']+)':\s*'([^']+)'", block))


def _leaf(data, key):
    for part in key.split('.'):
        data = data[part]
    return data


def test_mapa_cobre_exatamente_os_avisos_do_contrato_f2():
    canonicos = set(_f2().MENSAGENS_DE_ENCERRAMENTO.values())
    assert set(_display_map()) == canonicos


def test_textos_canonicos_continuam_gravados_por_terminate_session():
    for texto in _f2().MENSAGENS_DE_ENCERRAMENTO.values():
        assert f"terminateSession('{texto}')" in APP
    # O escritor não traduz: nenhuma chamada de tradução dentro de terminateSession.
    corpo = _f2()._corpo_de(APP, 'terminateSession')
    assert 'tr(' not in corpo and 'EpiI18n' not in corpo and 'trEpi' not in corpo


def test_apaga_antes_de_exibir_e_so_entao_traduz():
    body = _consume_body()
    remove = body.index('sessionStorage.removeItem(SESSION_END_MESSAGE_KEY')
    assert remove < body.index('avisosCanonicos') < body.index('setLoginMessage(')
    # A tradução não escreve em storage nem dispara eventos de sessão.
    depois = body[remove:]
    for proibido in ('sessionStorage.setItem', 'localStorage', 'terminateSession(', 'clearSession(',
                     'dispatchEvent', 'location.reload'):
        assert proibido not in depois, proibido


def test_equivalencia_nos_cinco_idiomas():
    cats = {loc: json.loads((ROOT / 'static/i18n' / f'{loc}.json').read_text(encoding='utf-8')) for loc in LOCALES}
    for texto, chave in _display_map().items():
        assert _leaf(cats['pt-BR'], chave) == texto, (chave, 'pt-BR deve exibir exatamente o texto canônico')
        for loc in LOCALES[1:]:
            valor = _leaf(cats[loc], chave)
            assert valor and valor != texto and '{' not in valor, (loc, chave, valor)


def test_aviso_fora_do_mapa_aparece_como_veio():
    body = _consume_body()
    assert ': pendente;' in body.replace('\n', ' ').replace('  ', ' ') or ': pendente' in body
