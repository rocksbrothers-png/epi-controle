"""Guarda: `data-i18n-value` nunca em `<option>` nem em campo de formulário.

Regressão (docs/UBX_APPJS_AUDITORIA.md §15.4): o `i18n.js` mapeia
`data-i18n-value` para o atributo `value`. Nas opções do `<select name="active">`
do formulário de Empresas isso trocava `1`/`0` por "Ativa"/"Inativa" (ou o texto
traduzido), o seletor ficava sem valor e o formulário enviava `active: ''` — o
backend recusava ("Campo obrigatório: active") e cadastrar/editar Empresa pelo
web falhava em todos os idiomas. O `value` de um campo é o dado enviado ao
backend e não pode depender do idioma; o texto visível se traduz com `data-i18n`.
"""

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'
ARQUIVOS = sorted((STATIC / 'views').glob('*.html')) + [STATIC / 'index.html']
# Elementos cujo `value` é enviado (ou lido pelo formulário).
CAMPOS = {'option', 'input', 'select', 'textarea', 'button'}


class _Coletor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.achados = []

    def handle_starttag(self, tag, attrs):
        nomes = {nome for nome, _ in attrs}
        if tag in CAMPOS and 'data-i18n-value' in nomes:
            self.achados.append((self.getpos()[0], tag, dict(attrs)))

    handle_startendtag = handle_starttag


def _achados(caminho):
    coletor = _Coletor()
    coletor.feed(caminho.read_text(encoding='utf-8'))
    return coletor.achados


def test_arquivos_existem():
    assert (STATIC / 'index.html').is_file()
    assert (STATIC / 'views' / 'empresas.html').is_file()


def test_nenhum_campo_enviado_usa_data_i18n_value():
    falhas = [
        f'{caminho.relative_to(ROOT)}:{linha} <{tag}> data-i18n-value="{attrs["data-i18n-value"]}"'
        for caminho in ARQUIVOS
        for linha, tag, attrs in _achados(caminho)
    ]
    assert not falhas, (
        'data-i18n-value troca o value enviado pelo texto traduzido; use data-i18n '
        'para traduzir o rótulo e mantenha o value fixo:\n' + '\n'.join(falhas)
    )


def test_select_de_status_da_empresa_envia_1_e_0_com_rotulo_traduzido():
    texto = (STATIC / 'views' / 'empresas.html').read_text(encoding='utf-8')
    assert '<option value="1" data-i18n="company.active">Ativa</option>' in texto
    assert '<option value="0" data-i18n="company.inactive">Inativa</option>' in texto


def test_detector_pega_o_padrao_do_defeito():
    """Âncora: sem isso, um parser que não visse as opções passaria em silêncio."""
    coletor = _Coletor()
    coletor.feed('<select name="active"><option value="1" data-i18n-value="company.active">Ativa</option></select>')
    assert [(tag, attrs['value']) for _, tag, attrs in coletor.achados] == [('option', '1')]
