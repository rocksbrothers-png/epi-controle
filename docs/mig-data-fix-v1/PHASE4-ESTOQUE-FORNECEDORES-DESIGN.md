# Fase 4 — Estoque e Fornecedores no Centro de Migração (design/contrato)

Completa dois dos cinco cards "Em breve" do Centro de Migração (ADR-0003 §9):
**Estoque** (`unit_epi_stock`/`stock_movements`) e **Fornecedores**
(`outsourced_companies` + vínculo por Unidade). Os outros três permanecem
bloqueados por decisão (Usuários = escalada de privilégio; Empresas = criar
tenant; Solicitações = baixo valor) — ver `catalog.py`.

## Problema estrutural comum

O motor hoje grava **uma** tabela por linha, via `INSERT`/`UPDATE` cru montado
da allowlist do catálogo (`_insert`/`_update` em `service.py`). Os dois cards
desta fase exigem **escrita por serviço de domínio** com efeito em mais de uma
tabela:

- **Estoque**: um movimento (`stock_movements`, o razão) **e** o saldo
  (`unit_epi_stock`). O catálogo exige "importar como MOVIMENTO de ajuste,
  nunca como saldo" — gravar `unit_epi_stock` direto deixaria saldo sem
  movimento que o explique, quebrando a invariante do módulo de estoque.
- **Fornecedores**: a empresa (`outsourced_companies`) **e** o vínculo
  (`outsourced_company_unit_links`). Sem o vínculo, a empresa importada ficaria
  disponível para todas as Unidades (o buraco que o bloqueio original evitava —
  ver `catalog.py::_FORNECEDORES`).

### Abstração de writer/reverser (mudança no motor)

Dois campos novos, opcionais, em `EntityDescriptor` (late-ref `"módulo:função"`,
mesmo padrão de `normalizer`):

- `writer`  — substitui `_insert`/`_update` **da linha-alvo**. Grava a linha de
  `target_table` **pelo serviço de domínio** (que também faz o efeito
  secundário: o movimento, ou o vínculo) e devolve o `target_id`. O motor segue
  com a MESMA maquinaria: evidência (`_persisted_evidence`), registro
  (`_record`) e **reconciliação** (`_reconcile_job`) continuam verificando a
  linha de `target_table` — porque o writer grava justamente essa linha.
- `reverser` — chamado **uma vez por job** no `revert_job`, para desfazer os
  **efeitos secundários** (os movimentos do job; o vínculo criado). O rollback
  genérico já restaura/apaga as linhas de `target_table`; o reverser só limpa o
  que está fora dela.

Invariantes preservadas: allowlist (nomes ainda vêm do catálogo, nunca do
arquivo), SAVEPOINT por linha, serialização por tenant (`companies FOR UPDATE`),
`preview_token` anti-stale, reconciliação pós-escrita, e o gate
`require_enabled_entity` antes de qualquer escrita.

## Estoque (`estoque`)

- `target_table = 'unit_epi_stock'`, `natural_keys = ('unit_id','epi_id')`.
- Campos: `unit_id` (req., resolve `units.name`), `epi_id` (req., resolve
  `epis.name`), `quantity` (req., `int`), `notes` (opcional).
- **Semântica SET** (saldo inicial declarado, não delta acumulado): o saldo é
  ajustado PARA a quantidade importada. Reimportar o mesmo arquivo → delta 0 →
  `skipped`. É o que torna a importação idempotente **sem** coluna/índice novo.
- **Writer** (`modules.stock.service:migration_stock_writer`): por linha,
  `previous = saldo atual`, `new = quantidade importada`; se `delta == 0` →
  skip; senão `create_stock_movement(movement_type='in' se delta>0 senão 'out',
  quantity=abs(delta), previous_stock=previous, new_stock=new,
  source_type='migration', source_id=job_id, notes)` **e**
  `upsert_unit_stock(new)`. Devolve o id da linha de `unit_epi_stock`.
- **Sem peças QR nem lotes**: legado não tem QR/lote/validade física. O saldo
  migrado entra como estoque **sem validade física** e cai naturalmente no fluxo
  já existente de **"pendentes de regularização"** (EST-V3.5-R2), onde lote e
  validade são informados depois. Encaixe deliberado — não inventa dado que o
  sistema de origem não tinha.
- **Rollback**: físico. O genérico restaura/apaga `unit_epi_stock`; o reverser
  (`...:migration_stock_reverser`) apaga `stock_movements WHERE source_type =
  'migration' AND source_id = job_id AND company_id = ?`. **Sem
  `reversal_column`** ⇒ o motor já RECUSA reversão pós-homologação (saldo pode já
  ter sido consumido por entregas; desfazer seria inseguro).

## Fornecedores (`fornecedores`)

- `enabled = True`; mantém `target_table='outsourced_companies'`,
  `natural_keys=('cnpj','legal_name')`, normalizer e `derived_columns` já
  modelados.
- **Novo campo obrigatório** `unit_id` (resolve `units.name`): a Unidade de
  destino, **por linha**. É o que fecha o buraco do bloqueio — nenhuma empresa
  entra sem Unidade escolhida.
- **Writer** (`modules.outsourced_companies.service:migration_outsourced_writer`):
  chama `create_outsourced_company(payload, company_id, actor, unit_id=resolved)`
  — que já grava a empresa **e** cria o vínculo idempotente. Devolve o id da
  empresa.
- **Rollback**: físico. O genérico apaga `outsourced_companies`; o reverser apaga
  o(s) vínculo(s) criado(s) pelo job. Pós-homologação: sem `reversal_column` ⇒
  recusa (cadastro corporativo não se apaga em silêncio depois de aceito).

## Fora de escopo / não feito

- **Nenhuma migração de schema** (nem `supabase/migrations/*`, nem
  `core/schema.py`): os dois reusam tabelas e chaves existentes. Zero DDL em
  ambiente compartilhado.
- Usuários, Empresas, Solicitações continuam bloqueados (decisão de produto).
- Fila assíncrona (Fase 3) na UI segue como Fase 4+ do roadmap original.

## Testes (contrato + adversarial, PostgreSQL)

- Contrato: `estoque`/`fornecedores` cumprem o invariante de colunas NOT NULL
  (campos ∪ `column_defaults`), e o writer/reverser resolvem via late-ref.
- Estoque: insert novo; SET idempotente (reimport → skip); ajuste para baixo;
  movimento gravado com `source_type='migration'`; rollback apaga movimento e
  restaura saldo; multi-tenant (unidade/EPI de outro tenant → não resolve).
- Fornecedores: cria empresa+vínculo na Unidade; dedup por CNPJ; vínculo
  idempotente; sem `unit_id` → erro de linha (não entra sem Unidade); rollback
  apaga vínculo e empresa; isolamento por tenant.

## Governança

Byte-idêntico Corporate × SaaS em `modules/data_migration/`. MERGE = NÃO ·
DEPLOY = NÃO · MIGRAÇÕES COMPARTILHADAS = N/A (não há) · PRs draft.
