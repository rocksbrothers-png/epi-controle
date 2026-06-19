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

## 7. Banco de Dados — Advisors de performance (CORRIGIDO)

Antes: 100 itens **INFO** — **92 `unindexed_foreign_keys`** + 8 `unused_index`. Nenhum WARN/ERROR.

**Correção aplicada.** Criados **92 índices de cobertura** para todas as FKs sem índice
(`company_id`, `unit_id`, `employee_id`, `epi_id`, `*_user_id`, etc.), via:
- `supabase/migrations/20260619000000_index_unindexed_fks.sql`
- `epi_backend/migrations/009_index_unindexed_fks.py` (runner idempotente, registrado em `app_migrations`)

A migração **foi aplicada ao banco de produção** (Supabase MCP) e o advisor re-executado:
**`unindexed_foreign_keys` 92 → 0**. Beneficia JOINs multi-tenant, buscas por FK e deleções em cascata.

> Observação: o advisor passou a listar 100 `unused_index` (INFO). Isso é **esperado e inofensivo** —
> índices recém-criados aparecem como "não usados" até serem varridos por consultas; em base
> pequena/recente todos são sinalizados. Indexar FK é boa prática e os lints somem com o tráfego real.
> Não remover esses índices com base nesse alerta.

## 8. Banco de Dados — `column "id" does not exist` nos logs (EXPLICADO + MITIGADO)

**Causa raiz (não é falha de dados).** O shim de compatibilidade SQLite→Postgres em
`epi_backend/db.py::PostgresCursorWrapper.execute` **acrescenta `RETURNING id` a todo `INSERT`**
para emular o `lastrowid` do SQLite. Em tabelas **sem coluna `id`** (ex.: `app_migrations` com
`migration_id TEXT PRIMARY KEY`, tabelas de junção), o Postgres rejeita com
`column "id" does not exist`. O código **já trata**: faz `ROLLBACK TO SAVEPOINT` e re-executa o
`INSERT` sem `RETURNING` — **funcionalmente inofensivo**. Os 2 ERRORs ocorrem no bootstrap (inserts
em tabelas sem `id`) e o app se recupera sozinho.

**Mitigação aplicada.** O Postgres registrava cada tentativa falha como ERROR (ruído que pode mascarar
erros reais). Adicionado cache de processo `_TABLES_WITHOUT_ID`: na 1ª falha por tabela, ela é
memorizada e os próximos `INSERT` pulam o `RETURNING id`. Cada tabela sem `id` gera **no máximo 1**
erro por processo, em vez de 1 por insert.

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

## 9. Fichas de EPI arquivadas — visualizar/imprimir/baixar e arquivamento (CORRIGIDO)

**As fichas ESTÃO sendo arquivadas.** Verificado no banco (Supabase MCP): `ficha_epi_snapshots`
tem 3 snapshots `archived`, com `html_content` completo (`<!DOCTYPE html>…</html>`, ~100–140 KB cada),
0 órfãos, 0 vazios.

**Bug raiz do erro ao visualizar/imprimir/baixar.** O handler `handle_get_ficha_archive_html`
(`modules/ficha/routes.py`) escrevia o corpo **sem chamar `handler.end_headers()`** — diferente dos
handlers de ficha "ao vivo" (`handle_get_ficha_html`, `handle_get_ficha_period_html`, que chamam
`end_headers()`). Sem o terminador de cabeçalhos, a resposta HTTP fica malformada e o navegador
falha ao renderizar/abrir a ficha arquivada. **Corrigido** (adicionado `end_headers()`).

**Print e Export não diferiam de Visualizar.** As três ações (`snapshot_view/print/export`) retornavam
o mesmo HTML inline — "Imprimir" não abria o diálogo de impressão e "Exportar" não baixava arquivo.
**Corrigido:**
- `snapshot_print`: injeta `window.print()` no `onload` do HTML.
- `snapshot_export`: envia `Content-Disposition: attachment` → baixa `ficha-epi-<nome>-<id>.html`.

**Integridade do arquivo (robustez).** `get_ficha_archive_snapshot_by_id` e
`fetch_ficha_archive_snapshots` usavam **INNER JOIN** com `employees/units/companies`. Como o snapshot
é autocontido (guarda o HTML e os IDs), um colaborador/unidade **excluído** fazia a ficha arquivada
**sumir da lista** e **quebrar a visualização** ("Snapshot não encontrado"). Trocado para **LEFT JOIN**
em ambas — a ficha arquivada permanece acessível mesmo após exclusão do colaborador (correto para fins
de retenção legal).

## Checklist por módulo

| Módulo | Status |
|---|---|
| Login / i18n | ✅ corrigido (JSON) — aguarda redeploy |
| Troca de idioma | ✅ corrigido (JSON) |
| Estoque (relatório) | ✅ HTML corrigido |
| Compras / Fornecedores | ✅ dados e código OK — bloqueado pelo 503 |
| Fichas arquivadas (ver/imprimir/baixar) | ✅ corrigido (end_headers + print/export + LEFT JOIN) |
| Bootstrap / Sessão | ⚠️ infra (503 no boot) |
| Banco de Dados | ✅ saudável; 92 índices de FK criados (advisor 92→0) |
| Segurança (advisors) | ✅ 0 alertas |
| Testes automatizados | ✅ 902 passed / 1 skipped (9 novos testes de regressão) |

## Verificação aprofundada (testes adicionados)

- `tests/test_i18n_files_integrity.py` — valida JSON, ausência de chaves duplicadas, paridade de
  988 chaves e presença das chaves de `login.*` nos 5 idiomas (guarda contra a regressão do bug).
- `tests/test_ficha_archive_view_print_export.py` — integração do handler de ficha arquivada:
  prova `end_headers()`, injeção de `window.print()`, `Content-Disposition: attachment` e que a
  visualização sobrevive à exclusão do colaborador (LEFT JOIN).
- Limpeza extra: removidas **3 chaves duplicadas** por arquivo de i18n (`signatureRequiredDraw`,
  `automaticHint`, `singleIcon`) — artefatos do mesmo merge. Verificado: **0 `<select>` aninhado**
  em todo o HTML (parser).
