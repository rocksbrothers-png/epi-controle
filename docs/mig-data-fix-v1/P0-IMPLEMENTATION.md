# Fase 1 — proteções P0 e diagnóstico dos CIs

## Execuções RED identificadas por SHA

| Produto | HEAD do draft RED | PostgreSQL Migration Journey |
|---|---|---|
| Corporate PR #1034 | `eef05c220e1a1b55fdcd51b59d99d9dd148546b0` | run `38641141415`, job `116116637830` |
| SaaS PR #407 | `dc388349b719a4d2f1613c60a820df8cd13074f5` | run `38641154895`, job `116116686132` |

Ambos: 287 coletados, 270 aprovados, 17 falhas na etapa **Full tests_postgres
suite (catches files not listed above)**. Esses HEADs têm somente baseline,
matriz e novas regressões; não têm implementação P0. Portanto, os logs fornecidos
são o RED intencional, não uma regressão de implementação já corrigida.

Erros originais: fração aceita/truncada; infinito gera OverflowError; diagnósticos
sem entidade/severidade; rollback elimina edição mapeada ou não mapeada; FK deixa
transação abortada; erro depois do primeiro DELETE deixa mutação pendente; corrida
homologação/reversão elimina entrega oficial; repetições concorrentes retornam dois
sucessos. Nenhum teste P0 foi removido, marcado skip/xfail ou afrouxado.

No mesmo baseline: Backend CI, Security, CodeQL, Contract Tests, Backend Isolation
Guard e Portal Docs V1 concluíram success em ambos os produtos. Flutter CI não foi
acionado pelo filtro `flutter/**`; isso não equivale a teste Flutter aprovado.
Alguns jobs Security têm `continue-on-error` preexistente; seus steps devem ser
inspecionados, não inferidos somente pelo status externo do workflow.

## Implementação

- Homologação/reversão adquirem `FOR UPDATE` no job filtrado por empresa antes
  de verificar qualquer estado, mantendo lock até auditoria e commit.
- Reversão trava alvos por id crescente; valida tudo antes de modificar qualquer
  alvo. Operação suporta somente READ COMMITTED no PostgreSQL; outros isolamentos
  são recusados para não usar snapshot obsoleto nas consultas de dependência.
- Cada escrita de importação grava estado completo persistido em envelope
  `__rollback_v1__` no `after_json` existente, com `xmin/ctid` e estado anterior.
  Campos antigos do payload continuam presentes para compatibilidade de leitores.
- Comparação de todas as colunas detecta edições não mapeadas. Token PostgreSQL
  detecta também A→B→A. Jobs antigos sem prova completa não são reconstruídos a
  partir do estado atual: reversão automática é recusada.
- Múltiplas alterações do mesmo alvo no mesmo job são simuladas na ordem inversa
  para validar a cadeia, sem falsos conflitos por versões intermediárias.
- Metadados FK usam a relação efetiva e verificam referências inclusive em outros
  schemas e ON DELETE CASCADE/SET NULL. Lock do pai impede inserção concorrente de
  FK de atravessar o preflight. Nenhuma referência é filtrada por empresa, pois
  uma associação anômala entre tenants também deve impedir exclusão.
- `SET LOCAL row_security=off` somente na verificação de referências: não é bypass;
  o PostgreSQL recusa consulta se RLS ocultaria linhas. Falhas de metadados/permissão
  abortam a operação, nunca são interpretadas como ausência de dependências.
- Contagens insert/update da auditoria devem corresponder às do job. Cada mutação
  reversa exige rowcount=1 e leitura conciliada do estado persistido.
- Sucesso e callback da auditoria da rota comitam na mesma transação. Qualquer
  exceção faz rollback. Conflitos são registrados após rollback em transação limpa
  em `migration_job_records`, action `rollback_conflict`, sem valores pessoais.
- Quantidade usa Decimal finito, integral, positivo e no intervalo PostgreSQL
  INTEGER (1..2147483647); nenhum float/arredondamento/truncamento. Diagnóstico
  preserva `code/row/field/message/level` e acrescenta `entity/severity`.

Nenhuma tabela, coluna, migration ou dependência foi adicionada. O helper de
metadados SQLite fica na camada db já autorizada a executar PRAGMA. SQLite prova
contratos funcionais, não a segurança concorrente do PostgreSQL.

## Validação local inicial GREEN

Por produto: **430 passed** em suíte PostgreSQL completa e regressões unitárias
pertinentes (299 PostgreSQL + 131 unitários). Desses, 31 são novos casos P0 e de
segurança de snapshots, incluindo ABA, FK CASCADE/SET NULL e FK concorrente,
repetições concorrentes, falha de callback de auditoria e falha no segundo DELETE.
Ruff F401/F821 e git diff --check aprovados nos arquivos alterados.

A jornada antiga fazia upsert depois da importação e então exigia apagar o registro
alterado. Esse cenário passa agora a exigir recusa/preservação; a verificação de
rollback físico cirúrgico e segunda recusa continua ativa em importação nova,
sem alterações posteriores. Isso acrescenta proteção em vez de autorizar perda.

## Limitações e próximos gates

- Recusa conservadora se houver qualquer dependência FK, inclusive antes de
  reversão lógica. Não há política aprovada para desfazer decisões posteriores.
- `xmin/ctid` podem mudar em manutenção/rewrite do banco; consequência segura é
  conflito, exigindo análise humana. Snapshots completos aumentam auditoria/PII;
  retenção, autorização e isolamento existentes continuam obrigatórios.
- Não há prova automática de referências sem FK; nenhuma relação nova foi inventada.
- Processamento síncrono, fila, progresso, estados P1, parsers e UI permanecem fora
  desta autorização. P0 não certifica o Centro de Migração inteiro.
- A aprovação final depende de CI no novo HEAD e auditoria independente congelada.
  Fase 2, merge, deploy e mudanças compartilhadas continuam não autorizados.
