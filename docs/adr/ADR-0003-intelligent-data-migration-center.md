# ADR-0003 — Intelligent Data Migration Center

- **Status:** Aceito — implantação faseada. **PR 25 (esta PR): fundação
  backend** (permissão, módulo opt-in, schema, catálogo de entidades,
  registry de fontes de arquivo, motor de mapeamento inteligente, preview,
  estratégias, rollback, rotas REST e testes). Fases seguintes no §9.
- **Data:** 2026-08-06
- **Contexto de conformidade:** trabalhista, previdenciária, fiscal, LGPD e
  operacional (EPI)

## 1. Contexto

A maior barreira de entrada do EPI-CONTROLE não é preço nem funcionalidade:
é **implantação**. Todo cliente novo chega com uma base legada (planilhas,
TOTVS, Senior, Benner, Domínio, SAP, sistemas próprios em SQL Server/Oracle)
e a migração manual desses dados é o que trava a venda e alonga o
onboarding.

Este ADR define o **Intelligent Data Migration Center**: um centro de
migração de dados de nível enterprise, não uma "importação de Excel".

### 1.1 Correção de premissa técnica do pedido

O pedido de produto descreve a stack como "Python FastAPI". **Não é.** O
backend deste repositório é **HTTP puro da biblioteca padrão**
(`epi_backend/` + `core/router.py`, servido por gunicorn), com PostgreSQL em
produção e SQLite nos testes, através de um adaptador que traduz `%s`↔`?`.
Não há FastAPI, Pydantic, SQLAlchemy nem Alembic no projeto.

Este módulo segue a arquitetura **real**: `modules/<nome>/{service,routes}.py`,
migrações idempotentes em `core/schema.py` registradas em `core/bootstrap.py`,
autorização por `authorize_action` + `ensure_resource_company`. Introduzir
FastAPI aqui criaria uma segunda stack HTTP dentro do mesmo processo — custo
de manutenção e superfície de segurança dobrados, sem ganho.

`pandas` e `openpyxl` **já são dependências do projeto** (usadas em
relatórios), então XLSX/CSV/ODS não adicionam dependência nova.

## 2. Decisão

### 2.1 Um catálogo declarativo, não 20 importadores

O erro clássico seria escrever 20 importadores (um por entidade). Em vez
disso, cada entidade é um **descritor declarativo** (`catalog.py`):

```python
EntityDescriptor(
    key='colaboradores',
    label='Colaboradores',
    target_table='employees',
    natural_keys=('cpf', 'employee_id_code'),   # identidade p/ dedupe e update
    fields=(FieldSpec('name', required=True, aliases=(...)), ...),
    enabled=True,
)
```

O motor (parse → mapeia → valida → aplica → reverte) é **um só**, dirigido
por esses descritores. Adicionar uma entidade nova passa a ser adicionar um
descritor, não escrever um pipeline — é isso que torna as 20 entidades
viáveis e é o que permite às fases seguintes serem baratas.

### 2.2 Fonte = plugin com uma interface só

`sources.py` expõe `read_source(kind, payload) -> SourceDataset`, onde
`SourceDataset` é sempre `{columns, rows, diagnostics}`. Um XLSX, um JSON e
(nas fases seguintes) uma query em SQL Server produzem a MESMA estrutura —
o resto do pipeline não sabe de onde veio o dado.

### 2.3 A "IA" de mapeamento é determinística e auditável

O pedido fala em "IA de mapeamento". A decisão é **não** usar LLM aqui:
migração de dados cadastrais precisa ser **determinística, reproduzível e
explicável** (é dado trabalhista e fiscal). O motor usa, nesta ordem:

1. **match exato** por nome normalizado (sem acento/caixa/pontuação);
2. **dicionário de sinônimos PT/EN** curado (`Funcionário`/`Empregado`/
   `Employee` → Colaborador; `PPE` → EPI; `Registration`/`Matrícula`;
   `Department` → Unidade; `Warehouse` → Almoxarifado; etc.);
3. **fuzzy matching** (`difflib.SequenceMatcher`) acima de um limiar, com
   **score exposto na resposta**;
4. **fallback manual** — coluna não reconhecida sobe para o usuário mapear.

Cada sugestão retorna `{source_column, target_field, confidence, strategy}`,
então o usuário sempre vê *por que* o sistema propôs aquilo. E o mapeamento
confirmado é **salvo** (`migration_field_mappings`, por assinatura de origem)
e reaplicado automaticamente na próxima importação do mesmo layout — que é o
ganho real de produtividade em implantação.

### 2.4 Rollback é a decisão estruturante

Importação sem rollback é inaceitável em base trabalhista. Por isso
`migration_job_records` grava, **por linha**, `action` (insert/update/skip),
`target_table`, `target_id`, `before_json` e `after_json`.

Isso não é log: é o **estado necessário para desfazer**. Reverter é ler os
registros do job em ordem inversa, `DELETE` no que foi inserido e restaurar
`before_json` no que foi atualizado. Também é o que satisfaz "auditoria com
antes/depois" sem uma segunda estrutura.

### 2.5 Autorização — reaproveita o mecanismo existente, não cria um novo

- Permissão técnica nova e estreita: `data_migration:manage`, concedida
  **apenas** a `master_admin` e `general_admin`. Administrador Local, Gestor
  de EPI, Comprador, Aprovador e Colaborador nunca a recebem — conforme o
  pedido.
- Módulo estrutural `migracao` em `MODULE_KEYS`, **opt-in**
  (`_OPT_IN_MODULES`): nasce oculto em todo tenant, como
  `terceirizados`/`terceirizados_colaboradores` (ADR-0002 §10.3), e o
  Administrador Geral liga em Configuração → Regras → Visualização.
- `resolve_module_visibility()` continua reclampando pela permissão técnica:
  **é estruturalmente impossível** a configuração conceder Migração de Dados
  a um perfil que não tem `data_migration:manage`.
- Todo job é isolado por `company_id`; leitura e rollback passam por
  `ensure_resource_company`.

## 3. Modelo de dados

| Tabela | Papel |
|---|---|
| `migration_jobs` | Um job = uma importação. Entidade, fonte, hash do arquivo, estratégia, status, totais, tempos, ator, IP. |
| `migration_job_records` | Uma linha por registro tocado: ação, tabela/ID alvo, `before_json`, `after_json`, erro. Base do rollback e da auditoria. |
| `migration_field_mappings` | Mapeamento confirmado, por tenant + entidade + assinatura das colunas de origem. Reaplicado automaticamente. |

Todas isoladas por `company_id`, criadas por migração idempotente
(`ensure_data_migration_tables`), apenas aditivas — nenhuma tabela existente
é alterada.

## 4. Estratégias de importação

`insert_only`, `update_only`, `upsert`, `skip_duplicates`, `overwrite`,
`dry_run`. A identidade para dedupe/update vem das `natural_keys` do
descritor (ex.: CPF ou matrícula para colaborador) — nunca do ID interno do
sistema legado.

`dry_run` executa o pipeline inteiro **sem gravar**: é o preview.

## 5. Preview e validação

Antes de qualquer escrita o motor devolve: total de registros, duplicados
(no arquivo e contra a base), CPF inválido (dígito verificador), CA
inválido, obrigatórios ausentes, e referências inexistentes (empresa,
unidade, fornecedor, função). Cada diagnóstico carrega o número da linha —
sem isso o usuário não consegue corrigir a planilha.

## 6. Auditoria

Todo job registra ator, empresa, tenant, IP, origem, hash do arquivo,
data/hora, contagens e tempo. Cada linha registra antes/depois. Reversões
geram seu próprio evento. Reaproveita `register_company_audit`, sem
estrutura de auditoria paralela.

## 7. Segurança

- Gate de permissão + módulo em **toda** rota (o backend é a autoridade
  final; a UI só orienta).
- Isolamento por tenant em job, registros e rollback.
- Sem SQL dinâmico a partir de entrada do usuário: os nomes de tabela/coluna
  vêm **exclusivamente** do catálogo declarativo (allowlist), nunca do
  arquivo. Valores sempre por parâmetro. Esta é a defesa estrutural contra
  SQL injection na importação.
- Limite de tamanho de upload e de linhas por job.

## 8. Performance

Jobs acima do limiar (`_BACKGROUND_THRESHOLD_ROWS`) são marcados para
execução assíncrona com progresso persistido no próprio job
(`processed_rows`/`total_rows`). O executor em background entra na Fase 4
(§9) — nesta fase o limiar é aplicado e reportado, evitando que uma
importação de 100k linhas seja tentada de forma síncrona.

## 9. Roadmap faseado

| Fase | Escopo | Estado |
|---|---|---|
| 1 — Fundação (PR 25) | Permissão + módulo opt-in, schema, catálogo declarativo das 20 entidades, fontes de arquivo (XLSX/CSV/ODS/JSON/XML/TXT), motor de mapeamento inteligente, preview/validação, 6 estratégias, apply + rollback, rotas REST, testes | concluída |
| **2 — Web Legado (PR 26)** | Wizard de 4 etapas, dashboard com os 20 cartões, drag-and-drop, preview, download do relatório, histórico e rollback | **esta PR** |
| 3 — Flutter (Web/Android/iOS) | Mesma jornada, Material 3, responsivo, dark/light | seguinte |
| 4 — Escala | Executor em background, progresso incremental, importação parcial/incremental | seguinte |
| 5 — Fontes de banco | SQL Server, Oracle, MySQL, PostgreSQL, SQLite: testar conexão, listar tabelas, prever, migrar | seguinte |
| 6 — Fontes de API e ERP | REST, GraphQL, exports SAP/TOTVS/Senior/Benner/Domínio | seguinte |
| 7 — Binários | Documentos, fotos e assinaturas (PDF/JPG/PNG/DOCX) com vínculo automático e varredura antivírus | seguinte |

As entidades do catálogo já declaradas mas ainda sem writer vetado entram
como `enabled=False` e aparecem na UI como "em breve" — a alternativa
(expor um importador não validado para dado trabalhista) seria pior.

## 10. O que só apareceu rodando de verdade (PR 26)

A Fase 1 passou com 2 086 testes verdes e ainda assim **não importava um
único colaborador** no banco de produção. Três defeitos ficaram invisíveis
porque a suíte roda em SQLite e o produto roda em PostgreSQL. Ficam
registrados porque a causa é estrutural, não um descuido pontual.

**1. O `try/except` por linha não isolava nada no PostgreSQL.** O motor
promete que "uma linha ruim não derruba o job". No SQLite isso funciona; no
PostgreSQL o primeiro erro aborta a transação inteira e todo comando
seguinte falha com *current transaction is aborted* — inclusive o INSERT do
próprio diagnóstico e o UPDATE final do job. Pior: a conexão voltava
envenenada para o pool e derrubava a **requisição seguinte**, sem relação
com a importação. Corrigido com `SAVEPOINT` por linha (`_row_guard`), que é
o que torna a promessa real nos dois bancos.

**2. O preview mentia sobre o que ia acontecer.** `employees.unit_id` é NOT
NULL, mas o catálogo declarava a Unidade como opcional: a simulação dizia
"3 válidas, 0 problemas" e a gravação estourava em seguida. Um preview que
não prevê não serve para nada — o campo virou `required=True`.

**3. Nenhum export legado traz o ID interno deste sistema.** A planilha diz
"Produção", não "3". Sem tradução nome → id, a Unidade obrigatória tornaria
a importação impossível. Daí `FieldSpec.resolves_to`: o motor resolve pelo
nome dentro do tenant, aceita valor numérico como id (planilha exportada do
próprio sistema) e transforma nome inexistente em erro **no preview**, antes
de gravar.

Ainda derivado de (2): há colunas NOT NULL sem default que o catálogo nem
conhece (`employees.schedule_type`). O motor passou a introspectar a tabela
e preencher essas colunas com string vazia — o mesmo valor que o cadastro
manual do sistema grava. A introspecção mora em `epi_backend/db.py`
(`mandatory_db_columns`), único lugar autorizado a executar `PRAGMA`.

**Consequência de processo:** cobertura de teste alta não substitui exercitar
o produto contra o banco real. As fases seguintes devem incluir uma passagem
ponta a ponta em PostgreSQL antes de serem consideradas prontas.

## 11. Riscos

| Risco | Mitigação |
|---|---|
| Importação corrompe base de produção | `dry_run` obrigatório no wizard antes do apply; rollback por job; before/after por linha |
| Mapeamento errado silencioso | Score e estratégia expostos por coluna; preview mostra amostra já mapeada; usuário confirma antes de aplicar |
| SQL injection via nome de coluna do arquivo | Tabela/coluna sempre do catálogo (allowlist), nunca do arquivo |
| Vazamento entre tenants | `company_id` em job, registros e mapeamentos; `ensure_resource_company` na leitura e no rollback; testes de isolamento |
| Arquivo enorme derruba o processo | Limite de linhas e de bytes; jobs grandes marcados para background (Fase 4) |
| "IA" imprevisível em dado trabalhista | Decisão explícita de **não** usar LLM: mapeamento determinístico, reproduzível e explicável |
