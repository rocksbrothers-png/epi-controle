"""O rótulo de rastreabilidade impresso no rodapé da Ficha de EPI.

`ficha_epi_config.rastreabilidade` é TEXT desde sempre, e o rodapé da ficha o
imprime cru (`modules/ficha/service.py`). O app Flutter deste repositório,
porém, modelava o campo como `bool` e o oferecia como um `Switch` — o Lote 2b
corrige model e consumidor juntos.

Estes testes travam o lado do backend do contrato, porque é ele que decide o
que vai parar no papel. A combinação com o `Switch` produzia:

    ligado    → str(True) == 'True'  → o rodapé imprimia literalmente `True`
    desligado → False é falsy        → `or DEFAULT` restaurava o rótulo padrão

Nenhuma das duas posições fazia o que a tela prometia, e a posição "ligado"
gravava lixo num documento exigido pela NR-6.
"""

import sqlite3

from modules.settings.service import (
    DEFAULT_FICHA_RASTREABILIDADE,
    get_ficha_config,
    save_ficha_config,
)
from server_postgres import render_ficha_epi_html_document


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        'CREATE TABLE ficha_epi_config ('
        'id INTEGER PRIMARY KEY, company_id INTEGER, titulo TEXT, declaracao TEXT, '
        'observacoes TEXT, rastreabilidade TEXT, created_at TEXT, updated_at TEXT)'
    )
    return conn


def _rodape(config):
    html = render_ficha_epi_html_document(
        employee={'name': 'João', 'role_name': 'Operador', 'sector': 'Ops'},
        company={'name': 'ACME', 'logo_type': ''},
        unit={'name': 'Base'},
        deliveries=[],
        devolutions=[],
        config=config,
    )
    marcador = '<div class="rodape">'
    inicio = html.index(marcador) + len(marcador)
    return html[inicio:html.index('</div>', inicio)]


def test_rodape_imprime_o_rotulo_configurado():
    config = {
        'titulo': 'Ficha EPI',
        'declaracao': 'Declaração',
        'observacoes': 'Obs',
        'rastreabilidade': 'Ficha Individual de Controle de EPI - Ver. 01',
    }
    assert _rodape(config) == 'Ficha Individual de Controle de EPI - Ver. 01'


def test_rodape_nunca_recebe_a_representacao_textual_de_um_bool():
    # É este o defeito que o Lote 2b encerra do lado do app: com um bool no
    # payload, o backend persistia a string 'True' e ela ia impressa na ficha.
    conn = _conn()
    save_ficha_config(conn, 1, {'rastreabilidade': True})
    persistido = get_ficha_config(conn, 1)['rastreabilidade']

    assert persistido == 'True', (
        'o backend converte com str() — este teste documenta a corrupção que o '
        'Switch do app produzia; se a conversão mudar, revise o Lote 2b'
    )
    assert _rodape({'titulo': '', 'declaracao': '', 'observacoes': '',
                    'rastreabilidade': persistido}) == 'True'

    # E o que o app corrigido envia (String) chega íntegro ao papel.
    save_ficha_config(conn, 1, {'rastreabilidade': 'Ficha Individual de Controle de EPI - Ver. 01'})
    assert _rodape(get_ficha_config(conn, 1)) == 'Ficha Individual de Controle de EPI - Ver. 01'


def test_desligar_o_switch_nao_limpava_o_rotulo():
    # A outra metade da armadilha: `False` é falsy, então `or DEFAULT` repunha
    # o rótulo padrão. Desligar o Switch parecia funcionar e não fazia nada.
    conn = _conn()
    save_ficha_config(conn, 1, {'rastreabilidade': False})
    assert get_ficha_config(conn, 1)['rastreabilidade'] == DEFAULT_FICHA_RASTREABILIDADE


def test_rotulo_livre_sobrevive_ao_round_trip():
    conn = _conn()
    save_ficha_config(conn, 1, {
        'titulo': 'Ficha de EPI',
        'declaracao': 'Declaro ter recebido os EPIs.',
        'observacoes': 'Uso obrigatório.',
        'rastreabilidade': 'FIC-EPI Rev. 03/2026',
    })
    config = get_ficha_config(conn, 1)
    assert config['rastreabilidade'] == 'FIC-EPI Rev. 03/2026'
    # Sem regressão nos demais campos da mesma configuração.
    assert config['titulo'] == 'Ficha de EPI'
    assert config['declaracao'] == 'Declaro ter recebido os EPIs.'
    assert config['observacoes'] == 'Uso obrigatório.'
    assert _rodape(config) == 'FIC-EPI Rev. 03/2026'
