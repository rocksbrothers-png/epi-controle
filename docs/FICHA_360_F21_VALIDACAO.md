# F2.1 — evidências de validação e revisão adversarial

Bases: Corporate `b236b8b27329a182a0ddfbf6515ad7533212f99b`; SaaS
`a69b1a6c443f271f642e02148880b09443470d24`. Validação em 11/11/2026,
PostgreSQL **17.11 local**, bancos separados e descartáveis; nenhuma conexão
com produção. CI proposta usa PostgreSQL 16, não executado localmente.

## Resultado final pertinente

| Suíte | Corporate | SaaS |
|---|---:|---:|
| Autenticação 401/403, guarda atualizada explicitamente | 40 passaram | 40 passaram |
| Contrato F0/F1 | 56 passaram | 56 passaram |
| Contrato F2.1 | 22 passaram | 22 passaram |
| Guardas de domínio | 20 passaram | 20 passaram |
| F1 HTTP/PostgreSQL real | 25 passaram | 25 passaram |
| F2-T01..T18 HTTP/PostgreSQL real | 24 passaram | 24 passaram |
| Pool P0 HTTP/PostgreSQL real | 8 passaram | 8 passaram |
| Pool P0 e concorrência determinística | 53 passaram | 53 passaram |
| **Total pertinente final** | **248 passaram** | **248 passaram** |
| Harness JavaScript completo existente | 725 passaram | 725 passaram |
| Navegador F1, cinco idiomas, desktop/mobile | 35 passaram | 35 passaram |

JUnit final e planos integrais estão em `docs/evidence/F21_JUNIT_*.xml` e
`F21_PLAN_*.json`. Matriz dos cenários/preparação/resultados está em
`FICHA_360_F21_EPIS_EM_USO.md` e nos testes executáveis de mesmo identificador.

A execução geral `pytest tests/` também foi concluída:

- Corporate: 5435 passaram, 120 pulados, 4 falhas na execução inicial.
- SaaS: 5342 passaram, 124 pulados, 5 falhas na execução inicial.

Tratamento de **todas** as falhas dessa execução:

1. Guarda de autenticação esperava somente três arquivos. Atualizada para
   permitir explicitamente o adaptador HTTP F2.1. Sem novo ponto de geração
   de AuthenticationError no núcleo; 40 testes passaram novamente em ambos.
2. Três testes de Fastlane requeriam Ruby no PATH. Falhas reproduzidas na
   main Corporate sem alterações. Com Ruby 3.3.8 local, o arquivo inteiro
   passou nos dois produtos: 25 testes por produto.
3. No SaaS, o runtime compartilhado tinha PyMuPDF 2.1, enquanto o requirements
   SaaS exige 1.x. Falha reproduzida também na main SaaS. Com dependência
   de teste 1.28.2 instalada em diretório isolado, os 3 testes passaram.
   Nenhum requirements foi modificado.

Não se declara que a execução geral inicial foi verde nem que a suíte geral
inteira foi repetida após essas correções: os arquivos afetados foram
reexecutados, além dos 248 testes pertinentes finais. A suíte adicional de
cobertura de erros/i18n Corporate passou: 99 testes. A execução geral SaaS
não apresentou falha nessa suíte.

## Isolamento, auditoria e falhas

- A/B são empresas reais distintas nas fixtures; A1/A2 são unidades distintas.
- Local/Gestor com vínculo local ativo em A1 e pessoa operacional em A2 só
  recebem entregas A1; vínculo não amplia o predicado das linhas.
- Pessoa de B e inexistente produzem mesmo 404, inclusive com vínculo local
  inconsistente. Master e perfis sem ambas as permissões são bloqueados.
- Referência de produto/unidade de outro tenant é projetada como null, sem
  nome/categoria/ID do objeto externo.
- Cursor fabricado, de outro contexto ou reaproveitado após troca de unidade
  nunca amplia escopo. Remoção de autorização/papel é aplicada na próxima página.
- Auditoria foi lida da tabela real: evento concedido/negado e empresa do ator.
  Interrupção após INSERT e antes de commit causa rollback e impede 200.
- Saturação real de pool de uma conexão retorna 503, DB_POOL_SATURATED e
  Retry-After: 1; após liberar a vaga, nova consulta funciona.
- Divisão por zero SQL real e encerramento da própria sessão PostgreSQL
  retornam erro genérico, liberam/descartam a conexão e não deixam transação
  ociosa. O teste de sessão encerrada afirma descarte pelo pool existente.
- Consulta a pg_locks não encontrou advisory lock no banco de teste no ponto
  verificado. Código de runtime novo não adquire advisory lock.

## Métricas disponíveis

Carga F2.1: 48 requisições HTTP, 12 threads clientes, duas empresas intercaladas,
pool de teste limitado a 3. Zero respostas fora do escopo; zero falhas na carga.

| Métrica | Corporate | SaaS |
|---|---:|---:|
| Tempo total das 48 requisições | 0.689 s | 0.585 s |
| Pico em uso | 3 | 3 |
| Em uso ao final | 0 | 0 |
| Aberturas pendentes ao final | 0 | 0 |
| Devoluções pendentes ao final | 0 | 0 |
| Timeouts na carga | 0 | 0 |

Sem `idle in transaction` no ponto verificado após a carga e após erro SQL.
O plano foi medido após inserir **10 mil entregas da pessoa**, divididas entre
A1/A2, além das outras fixtures do banco. Resultado solicitado: 20 itens;
consulta interna obtém 21 para decidir o cursor. Cache quente, máquina local;
não representa capacidade de produção.

| Plano final | Corporate | SaaS |
|---|---:|---:|
| Tempo do nó raiz (ms) | 25.419 | 29.649 |
| Linhas obtidas | 21 | 21 |
| Blocos compartilhados em cache | 1377 | 824 |
| Blocos compartilhados lidos | 0 | 0 |
| Blocos temporários escritos | 0 | 0 |

A revisão mudou a consulta para limitar antes de enriquecer por joins. Um
plano intermediário Corporate teve ~82 ms/30386 blocos em cache; o plano final
reduziu o trabalho de joins sem índice novo. Valores variam com fixtures/cache.
A normalização ainda pode ordenar candidatos; índices são análise futura.

## Revisão adversarial e preservação

Revisão pelo próprio implementador, sem alegar revisão humana independente:

- Repassados gates de permissão, pessoa, tenant e unidade, incluindo estado
  sem unidade, vínculo arquivado, referência cruzada e troca temporária.
- Bearer obrigatório em off/shadow/enforce; refresh token, base64/claims
  malformados e token expirado não chegam à consulta. Adaptador local não
  modifica os nove pontos oficiais de autenticação nem o despacho global.
- Calendarização protegida por CASE no SQL; sentinela não aparece como data.
  Entradas numéricas excessivas e cursor fora de BIGINT são recusados.
- Confirmados limite no servidor e ausência de consultas por item: a quantidade
  de consultas de página com 100 itens não cresce sobre a de página pequena.
- Falha de persistência da auditoria impede sucesso e desfaz escrita parcial.
- Falha de aquisição/rollback preserva o envelope local; saturação escapa para
  o tratamento P0 sem alteração.
- Comparação com as bases: sem mudança em core, epi_backend, app.py, static,
  summary.py, contract.py, migrations, permissões ou índices. F1 teve sua
  expectativa de registro de rotas atualizada no teste, não seu comportamento.

Arquivos de implementação, testes, workflow e documentação são idênticos nos
produtos. Divergência preexistente: faixa de PyMuPDF Corporate/SaaS; preservada.

## Riscos residuais e recomendação

Não foram verificados índices instalados, dados, latências ou certificação
operacional de produção. Cursor não é snapshot nem credencial; mudança já em
processamento pode terminar sob contexto previamente validado. Datas legadas
inválidas ficam ao final, sem correção persistente. Logs HTTP preexistentes
podem incluir parâmetros de consulta; a trilha própria F2.1 não grava cursor
bruto. Nada dessa infraestrutura de logs foi alterado neste escopo.

**APTO tecnicamente para merge da F2.1**, sujeito aos checks do PR e à aprovação
expressa do responsável. Sem merge, deploy ou alteração de produção nesta
entrega. F2.2, F2.3 e F2.4 não iniciadas.

## Correção dos bloqueios de CI e revisão — 12/11/2026

A auditoria posterior encontrou uma ocorrência `generic-api-key`, exclusivamente
no literal JWT de teste do workflow. Não houve evidência de credencial de produção;
a ocorrência foi reproduzida com Gitleaks 8.24.3 nos dois commits originais.
O aviso de permissão para publicar comentário no GitHub era secundário.

Correção adotada: `secrets.token_hex(32)` no runner, registro por `add-mask` e
transmissão por `GITHUB_ENV`, antes dos testes. Sem credencial de produção,
secret externo, nova permissão do token ou exceção em Gitleaks. O script de CI
foi executado localmente duas vezes por produto: chaves distintas, comando de
mascaramento correto e herança confirmada por um processo filho, sem divulgar
os valores. O commit único da F2.1 é reconstruído para que o intervalo do PR
não contenha o literal anterior; refs locais `recovery/f21-pre-ci-fix-*`
preservam a recuperação. Atualização remota somente com lease do SHA auditado.

Os avisos CodeQL foram tratados sem supressão: chamadas `send_json`/`_error`
como procedimentos, seguidas de retorno vazio; o helper de páginas termina com
`raise AssertionError` em vez de uma chamada cujo caráter excepcional não era
reconhecido pela análise. Nenhum assert ou teste foi removido.

Regressão posterior às correções, PostgreSQL 17.11 local: **248 passaram por
produto** (Corporate 27,18 s; SaaS 31,84 s), incluindo os 24 casos F2-T01..T18,
autorização, isolamento, auditoria, cursor, saturação/concorrência e F1.
Os JUnit versionados foram atualizados para esta execução. Planos e métricas
anteriores continuam como amostra histórica: o SQL de negócio não mudou.

A CI remota deve confirmar novamente Gitleaks, CodeQL e PostgreSQL 16.
Comentários só devem ser resolvidos após essa confirmação. Nenhuma alteração
em F1, P0/P0.1, RBAC global, esquema, índice, exceções dos scanners ou produção.
Esta seção documenta a correção posterior; os resultados gerais anteriores
permanecem registrados acima, sem serem apresentados como nova execução integral.
