"""SECURITY-OUTPUT-XSS-V2 — texto de cadastro nunca entra cru em HTML no frontend.

Generaliza a guarda da V1 (nome de empresa) para nomes de colaborador, unidade e
EPI e os textos que andam com eles (matrícula, setor, função, fabricante, CA,
motivo/responsável de arquivamento, títulos e descrições de alerta). Falha se um
template em static/ interpolar um desses campos logo após uma tag ou no texto que
a segue (`<td>${item.name}`, `<option>${item.code} - ${item.name}`), ou concatenar o campo
logo após uma tag (`'<td>'+(item.name||'')`), sem escape.

Escape aceito: `${escapeHtml(...)}`, `${esc(...)}`, `${escapeText(...)}` etc. — o
`${` passa a conter a chamada, não o campo. Ternários (`${item.ca ? ... : ''}`)
ficam de fora: o que eles devolvem é conferido pelo próprio padrão.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'static'
FIELDS = (
    'name|full_name|employee_name|employee_id_code|unit_name|current_unit_name|epi_name|epi_display_name|'
    'sector|role_name|employee_role|employee_sector|manufacturer|ca|epi_ca|empresa_origem|archive_reason|'
    'archived_by_name|actor_name|city|title|description|supplier|quantity_label|qr_code_value'
)
RAW = re.compile(r'>[^<>`$]*\$\{\s*[A-Za-z_]\w*\??\.(?:' + FIELDS + r')\b(?!\s*\?(?!\.))')
# Mesma regra para HTML montado por concatenação: '<td>'+(item.employee_name||'')+'</td>'.
CAT = re.compile(r'''>['"]\s*\+\s*\(?\s*[A-Za-z_]\w*\??\.(?:''' + FIELDS + r'|company_name)\b')

# Exceções justificadas: o valor não vem de cadastro.
ALLOWED = {
    # Página de pagamento: título das opções vem do dicionário de tradução da própria página.
    ('js/pagamento.js', '<span>${opt.title}'),
}


def _sources():
    yield ROOT / 'app.js'
    for path in sorted((ROOT / 'js').rglob('*.js')):
        if '/test/' not in path.as_posix():
            yield path


def _offenders():
    found = []
    for path in _sources():
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if (RAW.search(line) or CAT.search(line)) and not any(rel == f and snippet in line for f, snippet in ALLOWED):
                found.append(f'{rel}:{number}: {line.strip()[:120]}')
    return found


def test_record_text_never_interpolated_raw_into_html():
    assert _offenders() == []


def test_guard_detects_raw_interpolation():
    for raw in ('`<td>${item.name}</td>`', '`<option value="1">${item.employee_id_code} - ${item.name}</option>`',
                '`<div><strong>${item.epi_name}</strong></div>`', '`<td>${d.unit_name || \'—\'}</td>`',
                '`<strong>${item.title}</strong>`', '`<small>${row.archive_reason}</small>`'):
        assert RAW.search(raw), raw
    assert CAT.search("+'<td>'+(item.employee_name||'')+'</td>'")
    assert not CAT.search("+'<td>'+escapeText(item.employee_name||'')+'</td>'")


def test_guard_accepts_escaped_or_non_html():
    for safe in ('`<td>${escapeHtml(`${item.name}`)}</td>`', '`<td>${esc(item.unit_name || \'-\')}</td>`',
                 '`${item.name} ${item.employee_id_code}`.toLowerCase()',  # busca, não HTML
                 '`<td>${item.ca ? esc(item.ca) : \'-\'}</td>`', '`<td>${item.id}</td>`'):
        assert not RAW.search(safe), safe
