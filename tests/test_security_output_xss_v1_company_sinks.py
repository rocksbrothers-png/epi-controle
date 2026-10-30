"""SECURITY-OUTPUT-XSS-V1 — nome de empresa nunca entra cru em HTML no frontend.

O nome da empresa é editável pelo Administrador Geral (Minha Empresa) e aparece
para o Administrador Master em várias telas. Esta guarda falha se um template
voltar a interpolar `company_name` sem escape (`${item.company_name}` logo após
uma tag), em app.js ou nos módulos de view.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'static'
RAW = re.compile(r'>\s*\$\{\s*[A-Za-z_]\w*\??\.company_name\b')


def _sources():
    yield ROOT / 'app.js'
    for path in sorted((ROOT / 'js').rglob('*.js')):
        if '/test/' not in path.as_posix():
            yield path


def test_company_name_never_interpolated_raw_into_html():
    offenders = []
    for path in _sources():
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if RAW.search(line):
                offenders.append(f'{path.relative_to(ROOT)}:{number}')
    assert offenders == []


def test_guard_detects_raw_interpolation():
    assert RAW.search('`<td>${item.company_name}</td>`')
    assert RAW.search('`<small style="x"> ${d.company_name}</small>`')
    assert not RAW.search('`<td>${escapeHtml(`${item.company_name}`)}</td>`')
    assert not RAW.search("`${item.full_name} ${item.company_name || ''}`")  # texto de busca, não HTML
