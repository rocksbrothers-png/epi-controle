# ADR-0005 — Fonte operacional das migrations e desconexão do Supabase Preview

**Status:** aceito
**Data:** 2026-08-18
**Contexto gerador:** issue #892 — `Supabase Preview` cronicamente vermelho na `main`.

---

## Contexto

### Onde cada peça roda

| camada | onde vive | evidência |
|---|---|---|
| aplicação | **Render** | `render.yaml` — serviços `…-api` (Docker) e `…-web` (estático) |
| PostgreSQL de produção | **Supabase** | `DATABASE_URL` / `SUPABASE_URL` nas envVars do Render |

O Render hospeda; quem fornece o banco é o Supabase. Um projeto por repositório:

| repositório | projeto Supabase | região |
|---|---|---|
| `epi-controle-app` (SaaS) | `wlneevhqklboctghvdeo` | us-east-1 |
| `epi-controle` (corporativo) | `kkmskwmkhyssrxqbsrqv` | sa-east-1 |

### Como o esquema chega ao banco

**`epi_backend/migrations/*.py` é a fonte operacional das migrations.** São 25 módulos
Python, cada um com `MIGRATION_ID` e `run(connection)`.

`core/schema.py` é quem os aplica: `_discover_migration_modules()` varre
`epi_backend/migrations/[0-9][0-9][0-9]_*.py` em ordem, `_load_migration_module()`
importa cada um, e `run_pending_migrations()` executa os pendentes contra o
PostgreSQL — o mesmo banco Supabase — registrando o que aplicou na tabela
**`app_migrations`** (`migration_id`, `status`, `applied_at`), criada pelo próprio
runner.

**`supabase/migrations/*.sql` não é, atualmente, um caminho de aplicação via
Supabase CLI.** Nenhum dos dois repositórios é um projeto linkado da CLI: não
existe `supabase/config.toml` em lugar nenhum — o diretório `supabase/` contém
apenas `migrations/`.

## O que o `Supabase Preview` estava medindo

O check comparava `supabase/migrations/` com a tabela
`supabase_migrations.schema_migrations` do projeto remoto e falhava com
`Remote migration versions not found in local migrations directory.`

Ele nunca poderia passar, porque compara duas coisas sem relação:

**1. A interseção é vazia dos dois lados.**

| projeto | versões remotas | arquivos `.sql` locais | em comum |
|---|---|---|---|
| `kkmskwmkhyssrxqbsrqv` | 10 | 28 | **0** |
| `wlneevhqklboctghvdeo` | 3 | 29 | **0** |

**2. Os formatos denunciam origens diferentes.** Todo arquivo local usa timestamp
sintético (`…000000`, `…000001`, `…120000`); toda versão remota tem HH:MM:SS real
— a assinatura de conteúdo aplicado pelo dashboard ou pela API, que carimba a
versão no momento da aplicação em vez de tirá-la do nome do arquivo.

**3. São dois livros-razão no mesmo banco.** `supabase_migrations.schema_migrations`
é escrita pela CLI/dashboard do Supabase. `app_migrations` é escrita por
`core/schema.py`. O caminho real de migrations escreve na segunda; o check lia a
primeira.

## Decisão

> **Desconectar a integração Supabase↔GitHub do repositório `epi-controle`,
> eliminando o check `Supabase Preview`.**

Reconciliar o histórico (`supabase migration repair`) foi **rejeitado**. Ele
marcaria as 28 versões locais como aplicadas e deixaria o check verde enquanto a
CLI do Supabase continua não aplicando nada. Um check verde sobre uma linhagem
que ninguém opera é pior que o vermelho atual — ninguém desconfia dele. É o
mesmo defeito que a [ADR-0004](ADR-0004-feature-multiplataforma-concluida.md)
nomeia na sua última seção: *artefato que afirma verificar e não verifica*.

Nenhum estado remoto de banco foi alterado nesta decisão. Nenhuma migration foi
aplicada, reparada ou removida.

## O que **não** muda

A cobertura real do caminho de migrations continua inteira, e nenhum destes
gates é tocado:

| gate | o que exercita |
|---|---|
| **Migration Journey (PostgreSQL)** | jornada ponta a ponta de `epi_backend/migrations` contra PostgreSQL real — **este** é o gate do caminho operacional |
| **Backend CI** — Test & Coverage | suíte `pytest tests/` |
| **Backend CI** — Lint (ruff) | lint do backend |
| **Backend CI** — PostgreSQL Schema & Multi-Tenant | invariantes Multi-Tenant e validação de sintaxe SQL |
| **API Contract & Multi-Tenant Scope** | contratos de API e escopo por tenant |
| **CodeQL / Secret Scan / pip-audit / Dependency Review** | segurança |

Desligar o `Supabase Preview` não remove cobertura porque ele não tinha nenhuma:
não aplicava SQL, não exercitava o produto, e comparava um diretório contra um
histórico alheio a ele.

## Status de `supabase/migrations/*.sql`

**Representação auxiliar e legível do esquema. Não é fonte de verdade
operacional.** Quem manda é `epi_backend/migrations/*.py`.

Os arquivos **permanecem versionados**, por dois motivos:

1. **Não são inertes.** O job `PostgreSQL Schema & Multi-Tenant` (`backend-ci.yml`)
   os lê em dois passos: *Validate Multi-Tenant invariants (static)*, que
   **falha o build** se nenhuma migration referenciar `tenant_id`/`company_id` ou
   habilitar RLS/`CREATE POLICY`; e *Apply SQL migrations (dry validation)*, que
   detecta regressão de sintaxe (não bloqueante). Apagá-los hoje derrubaria um
   gate real.
2. Servem de leitura de referência do esquema em SQL, que os módulos Python não
   oferecem de forma direta.

**O pareamento com os módulos Python já divergiu** e nada percebeu: o principal
tem 29 `.sql` e este repositório tem 28 — falta
`20260715000000_user_password_policy.sql`, contraparte da mesma lacuna registrada
na #909. Um par que se separa em silêncio é exatamente o que precisa de guarda.

## Consequências

- O destino definitivo dos `.sql` (manter como representação, gerar
  automaticamente a partir dos módulos Python, ou remover) fica em decisão
  separada — **não** neste ADR, e **não** neste PR.
- A divergência `.py` × `.sql` precisa de um teste de contrato que a acuse. Hoje
  ela só apareceu porque alguém contou os arquivos à mão.
- Toda migration nova continua sendo escrita em `epi_backend/migrations/*.py`.
  Escrever apenas o `.sql` **não** altera nenhum banco.

## Passo manual — executado em 2026-08-18

A desconexão em si **não foi uma mudança de repositório**: o `Supabase Preview`
era criado por um GitHub App externo, não por um workflow em
`.github/workflows/` (o `details_url` do check apontava para o painel do
Supabase). Este ADR registrou a decisão; a execução foi no painel:

1. Supabase → projeto `kkmskwmkhyssrxqbsrqv` → **Settings → Integrations →
   GitHub** → repositório `epi-controle` desconectado.
2. GitHub → **Settings → Branches** → `Supabase Preview` removido dos
   *required status checks* de `main` — sem isso, toda PR passaria a esperar
   indefinidamente por um check que nunca mais chega.

### Como verificar que ficou desligado

O `Supabase Preview` não é um workflow, então não aparece na listagem de
Actions: a observação é feita pela **lista de checks de uma PR**. Se ele não
constar ali, o App não está mais gerando o check.

O par de referência já está no histórico: o check aparece na PR #913
(`skipped`, pré-desconexão) e **não** aparece em `epi-controle-app#247` —
repositório onde a integração nunca esteve conectada. A ausência numa PR aberta
depois da desconexão fecha a verificação.

## Referências

- Issue #892 — sintoma, investigação e decisão
- `core/schema.py` — `_discover_migration_modules`, `run_pending_migrations`, `app_migrations`
- `render.yaml` — hospedagem e origem do `DATABASE_URL`
- `.github/workflows/postgres-migration-journey.yml` — o gate que realmente exercita as migrations
- `supabase/migrations/README.md` — status dos arquivos SQL
