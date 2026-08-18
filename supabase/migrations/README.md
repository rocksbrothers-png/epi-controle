# `supabase/migrations/` — representação auxiliar, não caminho de aplicação

> **Estes arquivos `.sql` não alteram nenhum banco.** Escrever um `.sql` aqui e
> fazer merge **não** aplica nada em produção.

A fonte operacional das migrations é **`epi_backend/migrations/*.py`**. Quem as
aplica é `core/schema.py` (`run_pending_migrations`), contra o PostgreSQL de
produção — hospedado no Supabase — registrando o que aplicou na tabela
**`app_migrations`**.

Este diretório é uma **representação auxiliar e legível** do esquema em SQL. Não
é fonte de verdade operacional, e não é aplicado pela CLI do Supabase: o
repositório não é um projeto linkado da CLI (não existe `supabase/config.toml`).

## Então por que os arquivos continuam aqui?

Porque **não são inertes**. O job `PostgreSQL Schema & Multi-Tenant`, em
`.github/workflows/backend-ci.yml`, lê este diretório:

- **Validate Multi-Tenant invariants (static)** — *falha o build* se nenhuma
  migration referenciar `tenant_id`/`company_id`, ou se nenhuma habilitar
  `ROW LEVEL SECURITY` / `CREATE POLICY`;
- **Apply SQL migrations (dry validation)** — aplica os arquivos em ordem num
  PostgreSQL efêmero para pegar regressão de sintaxe (não bloqueante).

Apagá-los hoje derrubaria um gate real de isolamento Multi-Tenant.

## Ao escrever uma migration

1. O arquivo que **importa** é o módulo Python em `epi_backend/migrations/`, com
   `MIGRATION_ID` e `run(connection)`.
2. O `.sql` correspondente aqui é opcional do ponto de vista de execução, mas
   mantê-lo em par preserva a leitura de referência — e o pareamento **já
   divergiu** ao menos uma vez sem ninguém notar.

Contexto completo, incluindo por que o check `Supabase Preview` foi desligado:
[`docs/adr/ADR-0005-migrations-fonte-operacional.md`](../../docs/adr/ADR-0005-migrations-fonte-operacional.md).
