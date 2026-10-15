# MIG-DATA-FIX-V1 — Fases 0 e 1

Somente Fases 0 e 1 autorizadas. MERGE=NO, DEPLOY=NO, FORCE-PUSH=NO,
SHARED MIGRATIONS=NO, REAL DATA CHANGES=NO. Branch protection inalterada.
READY FOR HUMAN MERGE DECISION=NO até auditoria independente dos HEADs finais.

## Baseline congelado

- Corporate main: `42c72ca8ad76fb46841edded56e23286af6a795e` (PR #1033).
- SaaS main: `11954e868842bef370162105def0cceff2fa2c8a` (PR #406).
- Nova consulta de origin/main em 2026-10-14 não encontrou alterações concorrentes.
- Worktrees dedicadas; nenhum checkout de outro trabalho alterado.
- PostgreSQL 17.11 descartável local por socket Unix; bancos distintos
  `mig_fix_corporate` e `mig_fix_saas`; exclusivamente fixtures sintéticas.
- ADR-0003, catálogo, sources, mapper, preview, service, rotas, normalizadores,
  schema/migrations, interface e wrappers PostgreSQL inspecionados.
- Sete arquivos de `modules/data_migration`, interface de migração, normalizadores,
  permissões e wrappers relevantes são equivalentes entre os produtos.

## GREEN → RED antes da implementação

Suite existente por produto: **188 passed** (57 contrato/jornada PostgreSQL,
131 testes unitários pertinentes). Comando:

```sh
python -m pytest tests_postgres/test_migration_contract_postgres.py \
 tests_postgres/test_migration_journey_postgres.py tests/test_data_migration_center.py \
 tests/test_data_migration_contract.py tests/test_delivery_history_migration.py -q
```

Novas regressões `tests_postgres/test_migration_p0_postgres.py`, antes da correção:
**17 failed, 2 passed em cada produto**. Incluem quantidade fracionária/NaN/infinito/
limites int32, edição posterior mapeada/não mapeada, dependência FK, atomicidade,
rollback versus homologação e repetições concorrentes. A reprodução usa conexões
PostgreSQL reais, locks controlados e joins limitados. Não depende de sleeps longos.

A corrida original: bloquear job na conexão A, iniciar reversão na B, observar
B esperando lock, homologar na A e confirmar. O código antigo apaga o histórico
antes de esperar no UPDATE do job e depois confirma o DELETE.

Rollback antigo após edição: importar registro, editar/commit por caminho externo,
reverter job; perde edição ou apaga registro. Falha injetada no segundo DELETE deixa
primeira mutação pendente na conexão original até teardown. Quantidade 1.9 vira 1;
infinito pode escapar como OverflowError.

## Matriz e escopo congelados

`matriz-funcional-baseline.csv` congela nove entidades, campos reais/mapeáveis,
obrigatórios e impedimentos. Não habilitar novas entidades nesta rodada. Nenhum
schema deve ser criado para recuperar as antigas 20 entradas.

## Plano de commits e dependências

1. Baseline e regressões RED, PRs draft.
2. P0: serialização do job, snapshots completos/versionados, verificação de
   conflitos e referências, rollback atômico/auditável e quantidades estritas.
3. Regressões adicionais, GREEN→RED→GREEN, auditoria independente dos HEADs e CI.

Fase 2 depende do gate independente da Fase 1 e aprovação humana. Fase 3 exige
aprovação do desenho de jobs e política transacional/checkpoints. Não há autorização
nesta rodada para async, fila, commits parciais, UI estrutural ou novas entidades.

## Decisão técnica prevista para a Fase 1

Usar locks de job/registro no PostgreSQL e os JSONs existentes de auditoria para
estado completo e token de versão; não criar tabela/coluna. Recusar reversão quando
não houver prova do estado original (incluindo jobs legados), conflito ou dependência.
Verificar FKs CASCADE/SET NULL explicitamente. Auditoria de sucesso deve estar na
mesma transação; conflito deve sobreviver ao rollback da tentativa.
