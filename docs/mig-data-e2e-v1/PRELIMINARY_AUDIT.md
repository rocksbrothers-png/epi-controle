# MIG-DATA-E2E-V1 — auditoria independente preliminar

Data: 2026-10-25. Auditor: agente independente `/root/independent_audit`.

Bases: Corporate `f596a04c0136220f39a6cb77954f949d79f00b90`; SaaS `ac7e072261b528d3c75ed583377397987909d8e4`.

Esta auditoria não alterou implementação, branches ou bancos compartilhados. As provas usam dados sintéticos exclusivamente em PostgreSQL local `mig_data_e2e_audit`, autorizado pelo agente principal. Bootstrap aplicou 36 migrations. Código de reprodução: `preliminary_probes.py`; resultados completos: `corporate-preliminary.log` e `saas-preliminary.log`.

## Defeitos reproduzidos em ambos os produtos

| Achado | Prova PostgreSQL | Impacto e correção proposta |
|---|---|---|
| P1: rollback de fornecedor apaga vínculos criados depois da importação | Importar fornecedor na unidade A; criar vínculo B manualmente; rollback retorna `deleted=1`, sem erro, e reduz vínculos de 2 para 0 e fornecedores de 1 para 0. | Perda de alteração posterior. `migration_outsourced_reverser` apaga todos os vínculos antes do preflight. Capturar e conferir evidência dos efeitos secundários; recusar rollback quando houver vínculo novo ou alterado. |
| P1: upsert de fornecedor informa sucesso para unidade sem vínculo | Importar A; upsert mesmo CNPJ para B retorna `updated=1,failed=0`, persiste `unit_id=B`; disponibilidade operacional continua `A=true,B=false`. | Resultado não corresponde ao destino informado. Criar vínculo B com evidência reversível ou recusar claramente a operação antes de escrever. |
| P1: estoque importado não concilia com o modelo físico | Importar 100 retorna `inserted=1,failed=0`, um movimento; banco tem 0 peças e 0 lotes. `unit_balance`: físico 100, rastreado 0, elegível 0, livre 0, diferença de conciliação 100. | Saldo sem peças não entra na regularização de validade física. Writer só faz SET no agregado e grava movimento; contrato não suporta lote/fabricação/validade. Não certificar como importação completa com conciliação física. Implementar migração pelo domínio físico ou registrar bloqueador e dependência sem falso sucesso. |

## Defeitos confirmados por inspeção

- `static/app.js` não oferece homologação no Centro de Migração; endpoint existe, mas histórico só exibe reversão e relatório.
- Confirmação não possui guarda `draft.busy`; no início de `runDataMigration`, só botões Próximo/Prévia são desabilitados. Aplicar continua clicável até a resposta.
- `async_jobs.execute_claim` confirma negócio no commit de `run_migration` e finaliza controle da fila em transação posterior. Interrupção nesse intervalo deixa negócio aplicado e controle recuperável sem vínculo. Nova tentativa recebe prévia obsoleta e pode informar “nada aplicado” incorretamente.
- `async_jobs.submit` aceita e persiste entidades sem validação de catálogo. Categorias excluídas precisam ser recusadas no submit, análise e prévia, além do writer.

## Cobertura existente relevante

A base já possui jornadas PostgreSQL de unidades, colaboradores, EPIs; suites específicas de histórico, fornecedores e estoque; testes P0 de rollback com snapshots completos, ABA e referências posteriores; testes de identidade, números sem truncamento, formatos e segurança assíncrona. Os cenários de efeitos secundários de fornecedor, conciliação física de estoque e interrupção após commit de negócio não estão cobertos pelos testes existentes.

Este é um relatório preliminar. Não constitui auditoria dos HEADs finais nem aprovação da implementação corrigida.


## Correção após investigação adicional

Existe um fluxo separado de conciliação física, `reconcile_untracked_lot`, que cria
peças e lotes a partir de saldo agregado mediante contagem/evidência explícitas.
A ausência de peças após importar não implica impossibilidade de completar a
operação. A regressão final exercita essa conciliação e comprova diferença zero.
O suporte ausente é transportar os metadados físicos no arquivo do Centro.
Esta nota substitui qualquer conclusão preliminar mais ampla sobre regularização.
