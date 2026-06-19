# Auditoria Técnica do Sistema EPI — 2026-06-19

Varredura geral de erros (Frontend, Backend, Banco de Dados, APIs, i18n, Render/Supabase).

---

## Resultado Final

| Métrica | Valor |
|---|---|
| Erros/inconsistências analisados | 8 grupos |
| **Corrigidos neste commit (código)** | **3 críticos** (i18n JSON, troca de idioma, `<select>` aninhado) |
| Diagnosticados (infra / stale deploy) | 3 |
| Observações de baixo impacto | 2 |
| Saúde geral do sistema | **~90%** (núcleo saudável; pendências são infra/redeploy) |
| Suíte de testes | **893 passed, 1 skipped** |

---

## 1. CRÍTICO — i18n quebrado: textos aparecem como `login.title`, `login.username`… (CORRIGIDO)

**Causa raiz.** Os **5 arquivos** de tradução (`static/i18n/{pt-BR,en-GB,es-ES,fr-FR,nb-NO}.json`)
estavam **sintaticamente inválidos** (JSON malformado). Três defeitos de merge em cada arquivo:

1. Chave duplicada `productiveUx` inserida sem vírgula após `noEmployeesAvailable` (linha ~292);
2. Vírgula ausente entre membros (ex.: `allEmployees` → `signatureRequiredDraw`, linha ~800);
3. Chave `}` extra antes do fechamento do objeto raiz (linha ~1053).

**Impacto.** No frontend, `fetch('/api/i18n/<locale>').json()` lançava exceção → `_active`/`_fallback`
ficavam vazios. No backend, `modules/i18n/routes.py::_load_translations` capturava o erro
(`json.loads`), registrava `i18n.load_error` e **retornava `{}`** — ou seja, a API entregava
traduções vazias. Sem dicionário, a UI exibia as **chaves cruas**. Isto também explica o
**Erro #2 (troca de idioma não funciona)**: `setLang()` recarregava um JSON inválido e nada mudava.

**Correção.** Reparados os 5 arquivos para JSON válido, removendo as duplicatas/colchetes extras e
inserindo as vírgulas faltantes. **Paridade confirmada: 988 chaves em todos os idiomas, 0 faltando.**
Testes `test_i18n_dashboard_coverage.py` voltam a passar.

## 2. CRÍTICO — Troca de idiomas (PT/EN/ES/FR/NB) (CORRIGIDO)

Sintoma do mesmo defeito do item 1. Com o JSON válido, `EpiI18n.setLang()` passa a carregar o
dicionário, persistir em `localStorage['epi_language']` e re-traduzir o DOM. Persistência
(localStorage) e detecção por navegador já estavam corretas em `static/i18n.js`.

## 3. CRÍTICO — HTML inválido: `<select>` dentro de `<select>` (CORRIGIDO)

**Erro do console:** *"A `<select>` tag was parsed within another `<select>` tag"*
(`stock-movements-report-form-smr-movement-type`).

**Causa raiz.** Merge defeituoso no formulário de Relatório de Movimentações de Estoque duplicou o
bloco do campo "Tipo" e aninhou um `<select id="smr-epi">` dentro de `<select id="smr-movement-type">`,
com IDs duplicados. Presente em `static/index.html` e no fragmento `static/views/estoque.html`.

**Correção.** Removido o bloco corrompido em ambos os arquivos, mantendo o `<select>` correto
(opções *Todos / Entrada / Saída*). IDs duplicados eliminados.

## 4. Erro do console: `share-modal.js` — `Cannot read properties of null (addEventListener)` (DIAGNOSTICADO)

A versão **no repositório** (`static/share-modal.js`) **já é defensiva**: usa `safeOn()` que valida
`target` e `typeof target.addEventListener === 'function'` antes de registrar, e só liga após
`DOMContentLoaded`. O stack do console aponta `share-modal.js:1:135` (arquivo **minificado em 1 linha**),
ou seja, um **bundle antigo ainda servido pelo Render**. → **Pendente de redeploy**, sem alteração de código.

## 5. Erro do console: `GET /api/bootstrap … 503 Service Unavailable` (DIAGNOSTICADO — INFRA)

**Origem no código:** *health gate* de bootstrap (`epi_backend/bootstrap.py:68`,
`runtime_probe_response`). Retorna **503** com `error_code=DB_BOOTSTRAP_NOT_READY` enquanto
`DB_BOOTSTRAP_STATE.ready` for `False` (inicialização do banco não concluída).

**Evidência coletada (Supabase MCP):**
- Projeto `kkmskwmkhyssrxqbsrqv` → status **ACTIVE_HEALTHY**, Postgres 17.6.
- Logs do Postgres: conexões **autenticando com sucesso** (scram-sha-256). Banco acessível.
- Advisors de **segurança: 0 alertas**.

**Conclusão.** Não é falha de banco nem bug de código — é **prontidão de inicialização** do serviço
no Render (cold start do plano `starter`, e/ou variáveis de ambiente de conexão durante o boot).
O caminho `/api/bootstrap` **não** está na allowlist `BOOTSTRAP_READY_EXEMPT_PATHS`, então responde 503
até o boot terminar; o frontend então exibe "Sessão expirada". → **Verificar logs do Render e env vars
de conexão; o 503 deve cessar após o boot/redeploy.**

## 6. Módulo Compras — "empresas autorizadas não aparecem" (DIAGNOSTICADO — sem bug de dados/código)

**Evidência (Supabase MCP), usuário do print (`actor_user_id=9`):**
- `jefferson.aquino`, role `general_admin`, **company_id 2 (Norskan Offshore)**.
- `authorized_suppliers` da empresa 2: **11 registros, 11 ativos**.
- Schema correto: `authorized_suppliers.active INTEGER NOT NULL DEFAULT 1` (`core/schema.py:1554`);
  `fetch_authorized_suppliers` faz `SELECT *` e o frontend filtra `s.active`.

**Conclusão.** Dados, permissões e código estão corretos. O dropdown vazio é **sintoma do 503 (item 5)**:
sem `/api/bootstrap`, `_authorizedSuppliers` nunca é carregado. Resolve junto com o item 5.

## 7. Banco de Dados — Advisors de performance (BAIXO)

100 itens nível **INFO**: 92 `unindexed_foreign_keys` e 8 `unused_index`. Nenhum WARN/ERROR.
Recomendação (não urgente): indexar FKs de tabelas de maior volume e revisar índices não usados.

## 8. Banco de Dados — `column "id" does not exist` nos logs (BAIXO / INVESTIGAR)

2 ocorrências (ERROR) nos últimos ~100 registros de log do Postgres. Provável consulta referenciando
`id` em tabela/view sem essa coluna. Requer captura da query exata (log com `statement`) para correção.
→ **Intervenção manual: habilitar log de statement e isolar a origem.**

---

## Correções aplicadas (automáticas, neste commit)

- `static/i18n/pt-BR.json`, `en-GB.json`, `es-ES.json`, `fr-FR.json`, `nb-NO.json` — JSON válido, paridade 988 chaves.
- `static/index.html` — removido `<select>` aninhado no relatório de movimentações.
- `static/views/estoque.html` — idem.

## Pendências (intervenção manual / infra)

1. **Redeploy no Render** para publicar `share-modal.js` defensivo e o HTML/JSON corrigidos (resolve itens 1–4).
2. **503 bootstrap**: revisar logs do Render + env vars de conexão (item 5). Confirmar que o boot conclui.
3. Indexar FKs prioritárias (item 7).
4. Isolar `column "id" does not exist` via log de statement (item 8).

## Checklist por módulo

| Módulo | Status |
|---|---|
| Login / i18n | ✅ corrigido (JSON) — aguarda redeploy |
| Troca de idioma | ✅ corrigido (JSON) |
| Estoque (relatório) | ✅ HTML corrigido |
| Compras / Fornecedores | ✅ dados e código OK — bloqueado pelo 503 |
| Bootstrap / Sessão | ⚠️ infra (503 no boot) |
| Banco de Dados | ✅ saudável; FKs sem índice (INFO) |
| Segurança (advisors) | ✅ 0 alertas |
| Testes automatizados | ✅ 893 passed / 1 skipped |
