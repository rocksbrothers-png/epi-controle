# Registro de achados do Supabase Security Advisor

Evidências dos lints reportados pelo Supabase, guardadas no repositório para
que a correção tenha rastro e para que uma reincidência seja comparável com o
estado anterior.

Os CSVs são exportados do painel (**Advisors → Security → Export**) ou obtidos
via `get_advisors`. Nome do arquivo: `AAAAMMDD_<antes|depois>_<project_ref>_<apelido>.csv`.

## Projetos

| `project_ref` | Nome no painel | Papel | Região |
|---|---|---|---|
| `kkmskwmkhyssrxqbsrqv` | epi-control-system's Project | corporativo | sa-east-1 |
| `wlneevhqklboctghvdeo` | epi-controle-app | SaaS | us-east-1 |

---

## 2026-08-11 — RLS ausente nas tabelas do Centro de Migração

Issue: rocksbrothers-png/epi-controle-app#205
PRs: #206 (correção), #207 (endurecimento do guarda após review)

### O que foi reportado

| Projeto | Nível | Lint | Tabelas |
|---|---|---|---|
| corporativo | **ERROR** ×3 | `rls_disabled_in_public` | `migration_jobs`, `migration_job_records`, `migration_field_mappings` |
| SaaS | INFO ×3 | `rls_enabled_no_policy` | as mesmas três |

Arquivos: `20260811_antes_kkmskwmkhyssrxqbsrqv_corporativo.csv`,
`20260811_antes_wlneevhqklboctghvdeo_saas.csv`.

### Causa

As três tabelas nasceram no ADR-0003 (Centro de Migração), criadas em
`core/schema.py`, **depois** da fase 5 de RLS hardening. Nenhuma fase as
cobria.

A causa de fundo era mais ampla: as migrations de RLS criam policies
`TO anon, authenticated`, roles que só existem no Supabase. Em PostgreSQL puro
a migration `002` falhava e o runner **parava** — 1 de 22 migrations aplicadas.
Nenhuma das sete fases anteriores jamais foi exercitada em CI.

### O que foi feito

1. **Migration `020_rls_hardening_phase6`** cobrindo seis tabelas — as três do
   Centro de Migração mais `epi_evaluation_summary`, `purchase_pendencies` e
   `report_requests`, que têm migration própria mas são puladas em banco novo
   (a fase roda antes de a tabela existir e o `CONTINUE WHEN NOT EXISTS` as
   ignora).
2. **Roles `anon`/`authenticated` criados no workflow de CI**, para as
   migrations de RLS passarem a ser realmente aplicadas nos testes.
3. **Guarda estrutural** (`tests_postgres/test_rls_coverage_postgres.py`): em
   vez de lista fixa, descobre as tabelas do catálogo e exige RLS + policy
   efetiva (`RESTRICTIVE`, `FOR ALL`, `USING (false)`, cobrindo os dois roles).
   Tabela nova sem cobertura quebra o CI no PR que a cria.
4. **Aplicação direta nos dois projetos** em 2026-08-11, via `apply_migration`,
   porque as migrations só rodam no deploy e o achado era de segurança.

### Estado após a correção

Verificado no catálogo dos dois projetos:

```
corporativo : sem_rls=0  rls_sem_policy=0  total=79
SaaS        : sem_rls=0  rls_sem_policy=0  total=78
```

Policy conferida em cada uma das seis tabelas:
`RESTRICTIVE | roles={anon,authenticated} | cmd=ALL | qual=false`.

### Impacto no sistema — nenhum

- O backend conecta como `postgres`, que tem `rolbypassrls = true`. As policies
  não o afetam. Confirmado por consulta ao catálogo.
- `SUPABASE_ANON_KEY` está declarada em `render.yaml` mas **não é usada em
  nenhum código** Python, Dart ou JS — o acesso é sempre por conexão direta
  (`DATABASE_URL` + psycopg2), nunca por PostgREST.
- Leitura das três tabelas continua funcionando após a mudança.

### Sobre exposição de dados

As três tabelas estavam **vazias nos dois projetos** no momento da correção:

```
jobs=0  records=0  mappings=0   (corporativo e SaaS)
```

`migration_job_records` é a tabela que guardaria o payload das linhas
importadas, incluindo CPF. Como nunca houve linha gravada, **não havia dado
pessoal exposto** — a porta estava aberta, mas o cômodo estava vazio.

Isto corrige, para menos, o risco que a #205 estimava como "médio-alto": a
estimativa foi feita antes de conferir o volume, e o correto é registrar que
era um risco **potencial**, não realizado. A pergunta sobre leitura indevida
via PostgREST fica respondida por consequência: não havia o que ler.
