"""DEP-FIX-PILLOW-V1 — `requirements.txt` sem declarações duplicadas.

`requirements.txt` é a fonte canônica das dependências Python do backend: o
Dockerfile de produção, os workflows de CI, o `pip-audit` e o Dependabot
(`directory: "/"`) leem este arquivo. Linhas repetidas para o mesmo pacote
(havia `gunicorn`, `python-dotenv`, `pytesseract` e `pandas` em dobro) fazem o
Dependabot editar só uma das ocorrências: no bump do Pillow 12 → 13 ele inseriu
`Pillow>=13.0.0,<14` sem remover `Pillow>=12.3.0,<13`, e o pip passou a falhar
com `ResolutionImpossible` em todos os jobs que instalam o arquivo.

Também trava a política de faixa existente (`>=mínimo,<teto` em toda linha),
para que a deduplicação não troque reprodutibilidade por versões soltas.
"""

import re
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parent.parent / 'requirements.txt'
_NAME = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)')


def _requirement_lines():
    for number, raw in enumerate(REQUIREMENTS.read_text(encoding='utf-8').splitlines(), start=1):
        line = raw.split('#', 1)[0].strip()
        if not line or line.startswith('-'):
            continue
        yield number, line


def _normalized_name(line):
    match = _NAME.match(line)
    assert match, f'linha de requisito ilegível: {line!r}'
    # Normalização PEP 503: `Pillow`/`pillow`, `python_dotenv`/`python-dotenv`.
    return re.sub(r'[-_.]+', '-', match.group(1)).lower()


def test_cada_pacote_declarado_uma_unica_vez():
    seen = {}
    duplicates = []
    for number, line in _requirement_lines():
        name = _normalized_name(line)
        if name in seen:
            duplicates.append(f'{name}: linhas {seen[name]} e {number}')
        else:
            seen[name] = number
    assert not duplicates, 'requirements.txt com pacote repetido: ' + '; '.join(duplicates)


def test_toda_dependencia_mantem_faixa_com_minimo_e_teto():
    # Só o especificador conta: um `<` em marcador (`; python_version<"3.12"`) não é teto.
    especificadores = [line.split(';', 1)[0] for _, line in _requirement_lines()]
    sem_faixa = [spec for spec in especificadores if '>=' not in spec or '<' not in spec.replace('<=', '')]
    assert not sem_faixa, f'dependência sem faixa >=mínimo,<teto: {sem_faixa}'


def test_pillow_continua_declarado():
    names = {_normalized_name(line) for _, line in _requirement_lines()}
    assert 'pillow' in names
