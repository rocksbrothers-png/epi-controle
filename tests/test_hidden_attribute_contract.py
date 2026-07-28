"""O atributo `hidden` precisa realmente esconder — inclusive em `<label>`.

Este teste existe por causa de um bug que passou por duas rodadas de correção
sem ser pego: o JS marcava `row.hidden = true` corretamente, mas o campo
"Empresa de Origem" continuava na tela.

Causa: `hidden` só esconde através da folha de estilo do NAVEGADOR, e qualquer
regra de autor que defina `display` ganha dela — independentemente de
especificidade. Como `styles.css` define `label { display: grid }`, todo
`<label hidden>` seguia visível.

Por que um teste de CSS e não de DOM: asserir `element.hidden` (a propriedade)
dá verde mesmo com o bug presente, porque o atributo *está* lá — ele só não
tem efeito visual. Foi exatamente esse falso verde que escondeu o problema.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _strip_comments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def _rules(css):
    """(lista_de_seletores, corpo) para cada regra de topo do arquivo."""
    for selectors, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        yield [s.strip() for s in selectors.split(',')], body


def test_hidden_attribute_is_enforced_globally():
    """Sem esta regra, cada campo condicional novo precisa do seu próprio
    remendo `[hidden] { display: none }` — e quem esquecer entrega um campo
    que nunca some.

    Exige o seletor **exatamente** `[hidden]`: já existem no arquivo regras
    escopadas (ex.: `.phase2-dropdown[hidden]`) que casariam com uma busca
    frouxa e dariam falso verde sem proteger o resto do app.
    """
    css = _strip_comments(_read('static', 'styles.css'))
    for selectors, body in _rules(css):
        if '[hidden]' in selectors and re.search(
            r'display:\s*none\s*!important', body
        ):
            return
    raise AssertionError(
        'regra global `[hidden] { display: none !important; }` ausente em '
        'styles.css — o atributo hidden volta a ser sobrescrito por '
        '`label { display: grid }` e afins. Regras escopadas como '
        '`.foo[hidden]` não valem: protegem só o próprio componente.'
    )


def test_global_display_rules_still_justify_the_important():
    """Guarda o *motivo* da regra acima.

    Se um dia não houver mais regra de autor ampla definindo `display` em
    elementos que usam `hidden`, o `!important` deixa de ser necessário. Até
    lá, remover a regra reintroduz o bug — este teste documenta isso ligando a
    causa ao efeito, para que a regra não pareça supersticiosa.
    """
    css = _strip_comments(_read('static', 'styles.css'))
    assert re.search(r'(^|\})\s*label\s*\{[^}]*display:', css), (
        'esperava ao menos uma regra global `label { display: ... }` — é ela '
        'que torna o !important necessário'
    )


def test_conditional_field_is_a_label_so_it_depends_on_the_rule():
    """O campo condicional real que motivou tudo isto é um `<label hidden>`,
    ou seja, cai exatamente no caso quebrado."""
    fragment = _read('static', 'views', 'colaboradores.html')
    match = re.search(
        r'<label[^>]*id="employee-empresa-origem-row"[^>]*>', fragment
    )
    assert match, 'campo Empresa de Origem não encontrado'
    assert 'hidden' in match.group(0), (
        'o campo precisa nascer com hidden — a visibilidade é decidida em '
        'runtime por syncEmpresaOrigemVisibility()'
    )
