"""Gate de drift entre `epi-controle` e `epi-controle-app`.

O gate existe porque 33 arquivos Dart divergiram entre os dois repositórios sem
nada no CI perceber — e só apareceram quando um gate de i18n tropeçou neles por
acidente. Estes testes cobrem as duas maneiras de um gate assim ser inútil:

- **rígido demais** — acusa como drift a diferença de identidade (bundle
  identifier, namespace) que DEVE existir. Vermelho permanente é gate desligado;
- **frouxo demais** — deixa passar mudança funcional, que é o que ele existe
  para pegar.
"""

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FLUTTER = RAIZ / 'flutter'
TOOL = FLUTTER / 'tool'


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, TOOL / f'{nome}.py')
    modulo = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOL))
    spec.loader.exec_module(modulo)
    return modulo


normalize = _carregar('parity_normalize')


def _hash(conteudo):
    return hashlib.sha256(normalize.normalizar(conteudo).encode()).hexdigest()


def _rodar_gate(*args):
    return subprocess.run(
        [sys.executable, str(TOOL / 'check_parity_drift.py'), *args],
        capture_output=True, text=True, cwd=FLUTTER,
    )


# ── diferenças legítimas continuam permitidas ────────────────────────────────

def test_bundle_identifier_diferente_nao_e_drift():
    aqui = "iosBundleId: 'com.rocksbrothers.epicontrole',"
    la = "iosBundleId: 'com.livamobile.epicontrole',"
    assert _hash(aqui) == _hash(la)


def test_namespace_da_organizacao_diferente_nao_e_drift():
    assert _hash('package com.rocksbrothers.epi_admin') == \
           _hash('package com.livamobile.epi_admin')


def test_firebase_options_esta_no_manifesto():
    # Prova viva da regra acima: este arquivo difere entre os repositórios em
    # exatamente uma linha (o `iosBundleId`) e mesmo assim entra no manifesto.
    # Se a normalização quebrar, ele sai — e o gate vira vermelho permanente.
    manifesto = json.loads((TOOL / 'parity_manifest.json').read_text(encoding='utf-8'))
    assert 'apps/epi_admin/lib/firebase_options.dart' in manifesto['files']


def test_toda_regra_de_normalizacao_tem_motivo_escrito():
    # Uma exceção sem justificativa é uma exceção que alguém amplia sem
    # entender. O motivo é parte da regra, não comentário solto.
    for _, marcador, motivo in normalize.REGRAS:
        assert marcador.startswith('<') and marcador.endswith('>')
        assert len(motivo) > 40, f'motivo raso para {marcador}'


# ── mudança funcional continua sendo pega ────────────────────────────────────

def test_mudanca_funcional_muda_o_hash():
    base = "if (isLoggedIn && mustChangePassword.value) {"
    alterado = "if (false && mustChangePassword.value) {"
    assert _hash(base) != _hash(alterado)


def test_normalizacao_nao_apaga_o_nome_da_organizacao_em_outros_contextos():
    # A regra do namespace é ancorada: `com.rocksbrothers` seguido de `.algo`
    # que não seja `epicontrole` NÃO pode ser colapsado junto com o app id,
    # senão dois pacotes distintos passariam a ter o mesmo hash.
    assert _hash('com.rocksbrothers.epicontrole') != _hash('com.rocksbrothers.outro')


# ── o gate em si ─────────────────────────────────────────────────────────────

def test_o_repositorio_esta_em_paridade_hoje():
    resultado = _rodar_gate()
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert 'Paridade preservada' in resultado.stdout


def test_o_gate_acusa_arquivo_alterado(tmp_path):
    manifesto = TOOL / 'parity_manifest.json'
    dados = json.loads(manifesto.read_text(encoding='utf-8'))
    alvo = next(iter(dados['files']))
    original = dados['files'][alvo]
    dados['files'][alvo] = '0' * 64
    backup = manifesto.read_text(encoding='utf-8')
    try:
        manifesto.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + '\n',
                             encoding='utf-8')
        resultado = _rodar_gate()
        assert resultado.returncode == 1
        assert alvo in resultado.stdout
        assert 'divergiram' in resultado.stdout
    finally:
        manifesto.write_text(backup, encoding='utf-8')
        assert json.loads(manifesto.read_text(encoding='utf-8'))['files'][alvo] == original


def test_o_gate_acusa_arquivo_que_sumiu():
    manifesto = TOOL / 'parity_manifest.json'
    backup = manifesto.read_text(encoding='utf-8')
    dados = json.loads(backup)
    dados['files']['apps/epi_admin/lib/nao_existe.dart'] = '0' * 64
    try:
        manifesto.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + '\n',
                             encoding='utf-8')
        resultado = _rodar_gate()
        assert resultado.returncode == 1
        assert 'sumiram' in resultado.stdout
    finally:
        manifesto.write_text(backup, encoding='utf-8')


def test_o_gate_falha_sem_manifesto(monkeypatch, tmp_path):
    # Sem manifesto o gate não pode passar em silêncio — é o mesmo erro do
    # `check_hardcoded_strings.sh`, que ficou verde meses sem varrer nada.
    manifesto = TOOL / 'parity_manifest.json'
    backup = manifesto.read_text(encoding='utf-8')
    try:
        manifesto.unlink()
        resultado = _rodar_gate()
        assert resultado.returncode == 2
        assert 'ausente' in (resultado.stdout + resultado.stderr)
    finally:
        manifesto.write_text(backup, encoding='utf-8')


def test_o_manifesto_cobre_o_que_ja_foi_sincronizado():
    # O manifesto não cobre tudo de propósito (ver docs/PARIDADE_ESPELHO.md),
    # mas precisa cobrir o que já foi entregue — senão o conjunto protegido
    # encolhe sozinho e o gate vira decoração.
    #
    # O Lote 1 (senha temporária) entra aqui assim que o seu PR mergear: o
    # manifesto só pode listar arquivos que JÁ estão em paridade, e gerá-lo a
    # partir de um branch não mergeado prometeria uma paridade que a `main` do
    # outro repositório ainda não tem. Regenerar depois do merge é o fluxo
    # normal da ferramenta, não uma exceção.
    manifesto = json.loads((TOOL / 'parity_manifest.json').read_text(encoding='utf-8'))
    for entregue in (
        'apps/epi_admin/lib/features/epis/epis_screen.dart',
        'apps/epi_admin/lib/features/users/users_screen.dart',
        'packages/epi_api/lib/endpoints/epis_api.dart',
        'apps/epi_admin/lib/core/bloc/epis_cubit.dart',
        'apps/epi_admin/lib/firebase_options.dart',
    ):
        assert entregue in manifesto['files'], f'{entregue} saiu da proteção do gate'


@pytest.mark.parametrize('lote_pendente', [
    'packages/epi_api/lib/models/employee.dart',
    'packages/epi_api/lib/models/ficha_config.dart',
    'apps/epi_admin/lib/features/dashboard/dashboard_screen.dart',
])
def test_o_manifesto_nao_promete_o_que_ainda_nao_esta_sincronizado(lote_pendente):
    # Incluir um arquivo ainda divergente faria o gate nascer vermelho no outro
    # repositório — e um gate que nasce vermelho é um gate que se desliga.
    manifesto = json.loads((TOOL / 'parity_manifest.json').read_text(encoding='utf-8'))
    assert lote_pendente not in manifesto['files']
