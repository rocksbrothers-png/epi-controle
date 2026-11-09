"""CO-1 — interface web do limite de alçada (módulos UBX de Compras).

* roda ``static/js/test/purchase-limits-runtime.js`` (módulos reais em vm);
* confirma que os três scripts carregam antes do ``app.js`` e que o cartão vive
  no fragmento de Configuração, oculto por padrão;
* confirma as chaves ``purchase.limits.*`` nos 5 idiomas (sem cópia do pt-BR e
  com os mesmos placeholders);
* confirma que ``static/app.js`` não conhece a alçada (nenhuma lógica nova no
  monólito).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
# Coincidências legítimas (mesma palavra no idioma), declaradas uma a uma.
SAME_WORD = {('es-ES', 'company')}
SCRIPTS = [
    '/js/modules/purchases/business/purchase-limits-rules.js',
    '/js/modules/purchases/integrations/purchase-limits-api.js',
    '/js/modules/purchases/ui/purchase-limits-view.js',
]


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js não disponível')
def test_runtime_dos_modulos_web():
    result = subprocess.run(['node', 'static/js/test/purchase-limits-runtime.js'], capture_output=True, text=True,
                            cwd=ROOT, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '11/11' in result.stdout


def test_scripts_carregam_antes_do_app_js_e_na_ordem_das_camadas():
    html = (ROOT / 'static/views/_scripts.html').read_text(encoding='utf-8')
    order = [m.group(1) for m in re.finditer(r'<script[^>]+src="([^"?]+)', html)]
    positions = [order.index(s) for s in SCRIPTS]
    assert positions == sorted(positions)
    assert positions[-1] < order.index('/app.js')


def test_cartao_no_fragmento_de_configuracao_oculto_por_padrao():
    html = (ROOT / 'static/views/configuracao.html').read_text(encoding='utf-8')
    card = re.search(r'<div[^>]+id="purchase-limit-config-card"[^>]*>', html)
    assert card and ' hidden' in card.group(0)
    for element in ('purchase-limit-input', 'purchase-limit-save-btn', 'purchase-limit-remove-btn',
                    'purchase-limit-current', 'purchase-limit-company', 'purchase-limit-feedback'):
        assert f'id="{element}"' in html, element
    assert 'style=' not in html[card.start():html.index('purchase-limit-feedback', card.start())]


def test_chaves_de_interface_nos_5_idiomas():
    cats = {loc: json.loads((ROOT / 'static/i18n' / f'{loc}.json').read_text(encoding='utf-8')) for loc in LOCALES}
    base = cats['pt-BR']['purchase']['limits']
    keys = set(base)
    assert {'title', 'notConfigured', 'invalid', 'saved', 'removed', 'tooLarge', 'removeConfirm', 'lastUpdate'} <= keys
    for loc in LOCALES[1:]:
        block = cats[loc]['purchase']['limits']
        assert set(block) == keys, loc
        for key, text in base.items():
            assert block[key], f'{loc}.{key}'
            if (loc, key) not in SAME_WORD:
                assert block[key] != text, f'{loc}.{key}: cópia do pt-BR'
            assert sorted(re.findall(r'\{(\w+)\}', block[key])) == sorted(re.findall(r'\{(\w+)\}', text)), f'{loc}.{key}'
    html = (ROOT / 'static/views/configuracao.html').read_text(encoding='utf-8')
    for key in re.findall(r'data-i18n="purchase\.limits\.(\w+)"', html):
        assert key in keys, key


def test_app_js_nao_conhece_a_alcada():
    app = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    for token in ('purchase-limits', 'purchase_limits', 'PURCHASE_LIMITS', 'po_approval_threshold', 'purchase-limit-'):
        assert token not in app, token
