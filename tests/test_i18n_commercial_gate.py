"""I18N-FULL-V1 — gate do Comercial e das funções sobrepostas com a UBX-V5.

A próxima etapa da UBX-V5 extrai o Comercial do ``static/app.js``. Este gate
garante que o código que vai ser movido já está internacionalizado e continua
assim: em cada função listada, todo literal de texto em português visível ao
usuário precisa ser argumento de ``tr``/``trEpi``/``textFor``/``attributeFor``/
``bindText`` (a chave do catálogo + o fallback pt-BR) ou constar da allowlist
abaixo, com o motivo.

As funções são procuradas pelo nome em ``static/app.js`` e, quando a UBX as
mover, em ``static/js/modules/**``. Se uma função sumir dos dois lugares o gate
falha: ou foi renomeada (atualize a lista) ou foi apagada.

O detector é léxico (strings, templates, comentários, regex) e não depende de
Node; ``test_detector_*`` prova que ele acusa o padrão do defeito.

Limites conhecidos (registrados, não escondidos): uma palavra isolada minúscula e
sem acento (``todos``) não é acusada, para não confundir com códigos canônicos; e
prosa escrita no lugar da CHAVE de ``tr()`` passa — a revisão do catálogo pega.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'static' / 'app.js'
MODULES = ROOT / 'static' / 'js' / 'modules'

FUNCTIONS = [
    # Sobrepostas com a UBX-V5 (docs/UBX_APPJS_AUDITORIA.md §15.1/§16.1).
    'formatCompanyCurrency', 'updateTopbarCompanyBadge', 'renderMyCompanyDomains',
    # Comercial.
    'planHintText', 'renderPlatformLogoPreview', 'renderPlatformLoginLogoPreview', 'contractStatusLabel',
    'renderCommercialContractPanel', 'resetCommercialContractForm', 'commercialRiskMeta', 'commercialActions',
    'renderCommercialSummaryCard', 'renderCommercialAlertCard', 'renderCommercialExpiringCard', 'renderCommercialStats',
    'renderCommercialSummary', 'renderCommercialAlerts', 'renderCommercialHistoryItem', 'renderCommercialHistory',
    'renderCommercialExpiring', 'populateCommercialActors', 'exportCommercialExcel', 'formatCommercialFiltersLabel',
    'printCommercialHistory', 'savePlatformBrand', 'saveCommercialContractDraft', 'generateCommercialContract',
    'signCommercialContractAction', 'fileToBase64', 'uploadSignedCommercialContract', 'sendCommercialContractByEmail',
    'exportCommercialHistory',
    # Login, troca de senha e Usuários (mesma continuação).
    'handleForcedPasswordChange', 'askTemporaryPassword', 'buildUserAccessMessage', 'saveUser',
    # Formulário dinâmico de EPI em teste (rótulos vêm de tr() nos chamadores).
    'openForm',
]

# (função, literal) aceitos sem tradução, com o motivo.
ALLOWED = {
    # Mapa de fallbacks pt-BR: cada valor é passado a tr(`commercial.contractStatusLabels.<código>`, ...).
    ('contractStatusLabel', 'Rascunho'), ('contractStatusLabel', 'Gerado'), ('contractStatusLabel', 'Enviado'),
    ('contractStatusLabel', 'Pendente de assinatura'), ('contractStatusLabel', 'Assinado'),
    ('contractStatusLabel', 'Ativo'), ('contractStatusLabel', 'Encerrado'), ('contractStatusLabel', 'Arquivado'),
    # E-mail do contrato: texto padrão do documento (contrato brasileiro), editável e enviado ao
    # contratante; mesma regra dos documentos assinados — não é texto de interface.
    ('renderCommercialContractPanel', 'Contrato comercial EPI Controle'),
    ('renderCommercialContractPanel', 'Segue contrato comercial para análise e assinatura.'),
    ('resetCommercialContractForm', 'Contrato comercial EPI Controle'),
    ('resetCommercialContractForm', 'Segue contrato comercial para análise e assinatura.'),
}

# trAccess: atalho local de buildUserAccessMessage para tr(`user.accessMessage.<chave>`, ...).
TRANSLATORS = {'tr', 'trEpi', 'textFor', 'attributeFor', 'bindText', 't', 'trAccess'}
TAG = re.compile(r'<[^>]*>')
BOUND_TEXT = re.compile(r'data-i18n="[^"]*"[^>]*>[^<]*')
ENTITY = re.compile(r'&[#\w]+;')


def _visible_prose(text):
    """Texto que o usuário leria: sem marcação (inclusive tags partidas pelo template),
    entidades e placeholders."""
    visible = text
    if '>' in visible and ('<' not in visible or visible.index('>') < visible.index('<')):
        visible = visible[visible.index('>') + 1:]  # resto de tag aberta no literal anterior
    if '<' in visible and '>' not in visible[visible.rindex('<'):]:
        visible = visible[:visible.rindex('<')]  # tag que continua no próximo literal
    visible = ENTITY.sub(' ', TAG.sub(' ', visible))
    visible = re.sub(r'\{\w+\}', ' ', visible)
    return ' '.join(visible.split())


def _is_prose(text):
    # Só o texto do PRÓPRIO elemento ligado a uma chave é traduzido pelo motor;
    # prosa fora dele continua sendo acusada.
    text = BOUND_TEXT.sub('>', text)
    visible = _visible_prose(text)
    if not visible:
        return False
    words = [w.rstrip('.,:;!?()') for w in visible.split(' ')]
    words = [w for w in words if w]
    if not words:
        return False
    if any(re.search(r'[_.:/=\\]|\w-\w', w) for w in words) and not re.search(r'[ãõçáéíóúâêôà]', visible, re.IGNORECASE):
        return False  # código, chave, seletor, arquivo, locale, classe CSS
    if re.search(r'[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]', visible):
        return True
    alpha = [w for w in words if re.fullmatch(r'[A-Za-zÀ-ÿ]+', w)]
    if len(alpha) >= 2 and len(alpha) == len(words):
        return True  # frase
    # Uma palavra Capitalizada (rótulo); códigos canônicos são minúsculos, snake_case ou SIGLAS.
    return len(words) == 1 and bool(re.fullmatch(r'[A-ZÀ-Ý][a-zà-ÿ]{2,}', words[0]))


def _lex(source):
    """Literais (texto, posição) com o nome da chamada que os envolve ('' se nenhuma)."""
    out, calls, i, n = [], [], 0, len(source)
    template_depth = []  # pilha de profundidade de chaves dentro de ${...}
    prev = ''  # último caractere significativo de código (para distinguir regex de divisão)
    ident = re.compile(r'[A-Za-z_$][\w$]*')

    def enclosing():
        return calls[-1] if calls else ''

    def read_template(j):
        """Lê um template a partir de j (após a crase); devolve (fim, partes de texto)."""
        parts, buf = [], ''
        while j < n:
            ch = source[j]
            if ch == '\\':
                buf += source[j:j + 2]; j += 2; continue
            if ch == '`':
                parts.append(buf); return j + 1, parts, None
            if ch == '$' and source[j + 1:j + 2] == '{':
                parts.append(buf); return j + 2, parts, 'expr'
            buf += ch; j += 1
        return j, parts, None

    while i < n:
        ch = source[i]
        if ch in ' \t\r\n':
            i += 1; continue
        if source.startswith('//', i):
            i = source.find('\n', i); i = n if i < 0 else i; continue
        if source.startswith('/*', i):
            i = source.find('*/', i) + 2; continue
        if ch in '\'"':
            j, buf = i + 1, ''
            while j < n and source[j] != ch:
                if source[j] == '\\':
                    buf += source[j + 1]; j += 2; continue
                buf += source[j]; j += 1
            out.append((buf, i, enclosing())); i = j + 1; prev = 'a'; continue
        if ch == '`':
            j, parts, state = read_template(i + 1)
            for part in parts:
                out.append((part, i, enclosing()))
            i = j
            if state == 'expr':
                template_depth.append(0); calls.append('${')
            prev = 'a'; continue
        if ch == '/' and (prev == '' or prev in '(,=:[!&|?{};+-*%<>~^'):
            j, in_class = i + 1, False
            while j < n:
                c = source[j]
                if c == '\\': j += 2; continue
                if c == '[': in_class = True
                elif c == ']': in_class = False
                elif c == '/' and not in_class: break
                j += 1
            i = j + 1
            while i < n and source[i].isalpha(): i += 1
            prev = 'a'; continue
        if ch == '{':
            if template_depth: template_depth[-1] += 1
            calls.append('{'); i += 1; prev = ch; continue
        if ch == '}':
            if template_depth and template_depth[-1] == 0 and calls and calls[-1] == '${':
                template_depth.pop(); calls.pop()
                j, parts, state = read_template(i + 1)
                for part in parts:
                    out.append((part, i, enclosing()))
                i = j
                if state == 'expr':
                    template_depth.append(0); calls.append('${')
                prev = 'a'; continue
            if template_depth: template_depth[-1] -= 1
            if calls: calls.pop()
            i += 1; prev = ch; continue
        if ch == '(':
            k = i - 1
            while k >= 0 and source[k] in ' \t': k -= 1
            m = re.search(r'([A-Za-z_$][\w$]*)\s*(?:\?\.)?\s*$', source[max(0, k - 80):k + 1])
            calls.append(m.group(1) if m else '('); i += 1; prev = ch; continue
        if ch == ')':
            if calls: calls.pop()
            i += 1; prev = 'a'; continue
        m = ident.match(source, i)
        if m:
            i = m.end(); prev = 'a'; continue
        prev = ch; i += 1
    return out


def _function_body(source, name):
    match = re.search(r'(?m)^\s*(?:async\s+)?function\s+' + re.escape(name) + r'\s*\(', source)
    if not match:
        return None
    start = source.index('{', source.index(')', match.end() - 1))
    # Varre para achar o fim do corpo respeitando strings e templates.
    body_source = source[start:]
    depth = 0
    i = 0
    n = len(body_source)
    while i < n:
        ch = body_source[i]
        if ch in '\'"`':
            quote, i = ch, i + 1
            nest = 0
            while i < n:
                c = body_source[i]
                if c == '\\': i += 2; continue
                if quote == '`' and c == '$' and body_source[i + 1:i + 2] == '{':
                    nest += 1; i += 2; continue
                if quote == '`' and nest and c == '}':
                    nest -= 1; i += 1; continue
                if c == quote and not nest: break
                i += 1
            i += 1; continue
        if body_source.startswith('//', i):
            i = body_source.find('\n', i); continue
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return body_source[:i + 1]
        i += 1
    return None


def _sources():
    yield APP, APP.read_text(encoding='utf-8')
    for path in sorted(MODULES.rglob('*.js')):
        yield path, path.read_text(encoding='utf-8')


def _untranslated(name, body):
    achados = []
    for text, _pos, call in _lex(body):
        if call in TRANSLATORS or not _is_prose(text):
            continue
        if (name, _visible_prose(text)) in ALLOWED:
            continue
        achados.append(text)
    return achados


def test_todas_as_funcoes_existem():
    faltando = [name for name in FUNCTIONS if not any(_function_body(src, name) for _p, src in _sources())]
    assert not faltando, f'funções não encontradas em app.js nem em static/js/modules: {faltando}'


def test_comercial_sem_texto_em_portugues_fora_do_catalogo():
    achados = []
    for name in FUNCTIONS:
        for path, src in _sources():
            body = _function_body(src, name)
            if body:
                achados += [f'{path.relative_to(ROOT)}:{name}: {t!r}' for t in _untranslated(name, body)]
                break
    assert not achados, 'texto em português sem tr()/catálogo:\n' + '\n'.join(achados)


def test_detector_pega_o_padrao_do_defeito():
    # Formas exatas do código antes da continuação I18N-FULL-V1.
    antes = '''function renderCommercialStats() {
  refs.commercialStats.innerHTML = [
    ['Faturamento mensal', monthlyTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })],
  ].map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div></article>`).join('');
}
function commercialActions(company) {
  const toggleLabel = canReactivate ? 'Reativar' : 'Suspender';
  return `<div><button class="ghost" data-company-commercial="${company.id}">Abrir contrato</button>${toggleLabel}</div>`;
}'''
    assert _untranslated('renderCommercialStats', _function_body(antes, 'renderCommercialStats')) == ['Faturamento mensal']
    achados = _untranslated('commercialActions', _function_body(antes, 'commercialActions'))
    assert 'Reativar' in achados and 'Suspender' in achados
    assert any('Abrir contrato' in a for a in achados)


def test_detector_nao_isenta_prosa_fora_do_elemento_ligado():
    codigo = '''function y() {
  return '<span data-i18n="k">Texto ligado</span> Texto livre sem chave';
}
function z() {
  return `<th>Empresa</th>${tr('commercial.panel.colAction', 'Ação')}`;
}'''
    assert _untranslated('y', _function_body(codigo, 'y')) != []
    assert _untranslated('z', _function_body(codigo, 'z')) != []


def test_detector_aceita_texto_traduzido():
    depois = '''function x() {
  const a = tr('commercial.panel.openContract', 'Abrir contrato');
  const b = `<span>${escapeHtml(tr('commercial.panel.noHistory', 'Sem histórico comercial registrado.'))}</span>`;
  const c = globalThis.EpiI18n?.textFor?.(el, 'k', 'Status do contrato: {status}', {}, {});
  return /não-é-texto/.test(a + b + c);
}'''
    assert _untranslated('x', _function_body(depois, 'x')) == []
