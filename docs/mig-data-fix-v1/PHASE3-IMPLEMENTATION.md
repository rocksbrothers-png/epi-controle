# Fase 3 — implementação da fila durável e recuperação

Implementa o contrato de `PHASE3-ARCHITECTURE-REVIEW.md` (13 condições) e torna
verdes os 9 testes RED congelados em `tests_postgres/test_migration_phase3_postgres.py`.
Nenhuma entidade de negócio nova; a feature fica **DESLIGADA por padrão**.

## O que foi entregue

- `modules/data_migration/async_jobs.py` — API da fila: `install_schema`,
  `submit`, `get`, `list_jobs`, `request_cancel`, `claim`, `execute_claim`,
  `run_once`. O worker reutiliza `run_migration` (sem segundo motor).
- `epi_backend/migrations/035_migration_async_jobs.py` — cria a tabela de
  controle `migration_async_jobs` (DDL idempotente, compartilhada com
  `install_schema`). PostgreSQL-only, aplicada no bootstrap.
- `modules/data_migration/routes.py` — endpoints `POST /api/data-migration/async/submit`,
  `GET /api/data-migration/async/jobs`, `GET /api/data-migration/async/jobs/{id}`,
  `POST /api/data-migration/async/jobs/{id}/cancel`. Gate `data_migration:manage`
  + módulo `migracao`; nunca expõem payload/ciphertext; erro sanitizado (HOLE-1).
- `scripts/migration_worker.py` — worker CLI com `preflight()` que bloqueia
  ativação insegura (flag OFF, SQLite, pooler de transação :6543, chave ausente,
  schema ausente), loop `run_once`, SIGTERM cooperativo, logs só com id/timing.

## Modelo de dados (`migration_async_jobs`)

Controle por tenant: `company_id`, `actor_user_id`, `entity`, `source_kind`,
`strategy`, `preview_token`, `request_key` + `request_fingerprint` (idempotência),
`status` (CHECK: queued/claimed/running/completed/completed_with_rejections/
failed/cancelled/recovering), `owner`, `attempt`, `lease_expires_at`,
`cancel_requested`, contadores, `result_job_id`→`migration_jobs.id`,
`input_ciphertext` (payload Fernet, nunca em claro) + `input_hash`.
`UNIQUE (company_id, actor_user_id, request_key)`.

## Garantias (condições atendidas)

- **Ordem de locks / deadlock**: advisory de **sessão** por job (sobrevive ao
  commit interno de `run_migration`, liberado em `finally`) → `companies FOR UPDATE`
  (dentro de `run_migration`) → refs/targets → controle por último, em
  transações curtas. Resolve o deadlock lease×`companies` do Codex.
- **Claim e fencing**: `FOR UPDATE SKIP LOCKED` (no máximo um vencedor) +
  `pg_try_advisory_xact_lock` (não rouba job com executor vivo); `execute_claim`
  revalida owner/attempt/lease/cancel sob a linha de controle antes de executar.
- **Sem sucesso enganoso**: preview não escreve; `execute_claim` reautoriza na
  execução (usuário desativado/sem permissão/tenant mudado → `failed`, nada
  aplicado); `preview_stale` e payload adulterado falham fechado; todas as linhas
  falhando → `failed`; conciliação do `run_migration` preservada.
- **Idempotência**: `(company_id, actor_user_id, request_key)` + fingerprint —
  mesma chave+conteúdo ⇒ mesmo job; conteúdo divergente ⇒ recusa.
- **Isolamento**: `company_id` sempre do ator autenticado; leitura/cancelamento
  escopados ao tenant; referência cross-tenant recusada.
- **Lease**: `clock_timestamp()` (não `NOW()` transacional); reclaim só de lease
  expirado e sem `cancel_requested`.
- **Payload**: Fernet com envelope autenticado (empresa/ator/hash/tipo); hash
  reverificado no decrypt; chave ausente/inválida falha fechado, nunca efêmera.
- **Operação**: flag OFF por padrão; sem DDL implícito no bootstrap web
  compartilhado além da migração numerada; worker recusa SQLite/pooler/schema
  ausente/chave inválida.

## Testes

- 9 congelados (`test_migration_phase3_postgres.py`) — contrato da API.
- 7 adversariais + 3 de worker (`test_migration_phase3_adversarial_postgres.py`)
  — fencing por attempt, reclaim de lease expirado, serialização por advisory,
  cancelamento durante execução, `preview_stale`/payload adulterado fail-closed,
  flag OFF, preflight do worker e `run_once` ponta-a-ponta.

```sh
DATABASE_URL=postgresql://.../<db_descartável> pytest \
  tests_postgres/test_migration_phase3_postgres.py \
  tests_postgres/test_migration_phase3_adversarial_postgres.py -q
```

## Residuais (fora desta fatia)

Provas process-level de recuperação (SIGKILL em pontos distintos, dois
recoverers, commit de resultado desconhecido) e o estado `recovering` ficam para
a fase de hardening de recuperação; a UI é a Fase 4. Processamento permanece
síncrono por arquivo (sem progresso/retomada parcial); cargas muito grandes ainda
podem gerar espera — benchmark e checkpoints são trabalho futuro declarado.

## Governança

Byte-idêntico Corporate × SaaS. MERGE = NÃO · DEPLOY = NÃO · MIGRAÇÕES EM
AMBIENTE COMPARTILHADO = NÃO · PROVISIONAMENTO DE INFRA = NÃO · BRANCH PROTECTION
= INALTERADA. PRs permanecem draft.
