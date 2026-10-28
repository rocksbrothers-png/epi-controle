# FIX-EMPRESAS-ACTIVE-V1 — campo Situação (ativa/inativa) do formulário de Empresas

Base: Corporate `c1c9ac6f` / SaaS `b936120a` (arquivos idênticos nos dois). Defeito registrado em
`docs/UBX_APPJS_AUDITORIA.md` §15.4; vem de #974.

## Defeito e causa (reproduzido no Chromium contra a `main`: 25/25 cenários falham nos 5 idiomas)

1. **Valor trocado pela tradução.** As opções do `<select name="active">` (`static/views/empresas.html`) usavam
   `data-i18n-value`. O `i18n.js` trata esse atributo como "traduzir o `value`", então troca `1`/`0` pelo texto
   traduzido ("Active"/"Inactive"…), enquanto o texto visível segue em português.
   - Ao cadastrar ou editar, o formulário define `active` = `'1'`/`'0'`. Nenhuma opção tem esse valor, então o
     seletor fica vazio e envia `active: ''`. O backend recusa ("Campo obrigatório: active"). **Cadastrar e editar
     Empresa pelo web falhava em todos os idiomas.**
   - Escolhendo a opção à mão, ia o texto traduzido, e o `int()` do backend falhava.
2. **Estado carregado errado.** `startEditCompany` usava `String(Number(company.active || 1))`. Para uma empresa
   inativa, `0 || 1` dá `1`: ela abria como **Ativa**. Com o item 1 corrigido, gravar a edição a reativaria em
   silêncio.

## Correção

- As opções passam a usar `data-i18n` (traduz só o texto) e mantêm `value="1"`/`value="0"`.
- `startEditCompany` usa `company.active ?? 1`, a mesma regra que `saveCompany` já usava.

O que não muda: backend, autorização (`companies:create`/`companies:update`, Administrador Master), regras de
negócio, ativar/inativar pela lista e o caminho de reativação de licença do backend.

## Testes

| Teste | `main` | Com a correção |
|---|---|---|
| `scripts/browser/fix_empresas_active.py` (Chromium, 5 idiomas): opções traduzidas com value 1/0; cadastro ativa (padrão) e inativa; editar ativa mantém 1; editar inativa abre e grava 0; trocar o estado nos dois sentidos | 25/25 falham | 25/25 |
| `static/js/test/empresas-active-runtime.js` (3): opções do select; nenhuma `<option>` das views com `data-i18n-value`; `startEditCompany` carrega 0/1 | 3 falham | 3 passam |
| `scripts/browser/ubx_companies.py`: as asserções `KNOWN-DEFECT` (`active == ''`) passam a exigir `'1'` | — | 20/20 |

A caracterização da UBX-V5 (`companies-view-runtime.js`) detectou a mudança no cenário `editar:inativa`. A
referência congelada (`fixtures/app-before-ubx-v5-companies.js.txt`) recebeu a mesma correção, com um comentário.
