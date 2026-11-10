# P0 — Estabilidade do pool PostgreSQL

Etapa de estabilização de infraestrutura. Nenhuma funcionalidade nova, nenhuma
migração, nenhuma mudança de permissão. Vale igualmente para Corporate e SaaS
(o código de conexão é idêntico nos dois produtos).

## 1. Diagnóstico (antes de qualquer mudança)

Todas as rotas pegam a conexão do mesmo jeito: `with closing(get_connection())`
(350 ocorrências, 0 fora do padrão em `modules/`, `core/`, `app.py`). Ou seja,
a devolução ao pool é garantida mesmo com exceção. O problema não estava nas
rotas; estava no pool e na borda do servidor.

| # | Hipótese inicial | Veredito | Evidência |
|---|---|---|---|
| 1 | Pool de 10 conexões que não espera quando esgota | **Confirmada, e é pior** | `SimpleConnectionPool` levanta `PoolError` na hora → HTTP 500. Além disso **não é thread-safe** (ver causa-raiz) |
| 2 | Fila HTTP de 5 com ~1 s de espera | **Confirmada** | `socketserver` usa `listen(5)`; SYN excedente é descartado e retransmitido após ~1 s |
| 3 | `release_connection` sem `rollback` | **Não era o defeito** | O `putconn` do psycopg2 já faz `rollback` quando a transação não está ociosa. O que faltava era o caso de **estado de sessão** (advisory lock), que `rollback` não desfaz |

### Causa-raiz

O servidor é um `ThreadingHTTPServer` (uma thread por requisição) usando
`psycopg2.pool.SimpleConnectionPool`, que a documentação do psycopg2 declara
não ser utilizável entre threads. Reproduzido:

* **O teto não é respeitado.** `_getconn` testa `len(_used) == maxconn` e só
  depois conecta; o `connect` libera o GIL. Com `maxconn=10` e 30 threads, 30
  conexões são abertas. Como o teste é de igualdade, depois de passar do teto
  ele nunca mais dispara.
* **A contabilidade corrompe.** `_getkey` não é atômico: chaves duplicadas
  deixam entradas órfãs em `_used` (`trying to put unkeyed connection`,
  `KeyError`), e o pool passa a se declarar esgotado sem estar — o
  "esgotamento" observado em produção.
* **Sem espera.** Esgotado (de verdade ou por contabilidade), a resposta é
  500 imediato.

Achados adicionais:

* `core/bootstrap.py` e `modules/data_migration/async_jobs.py` usam advisory
  lock de **sessão**. Se o `pg_advisory_unlock` falhasse, a conexão voltava ao
  pool segurando o lock (resíduo "P2-B", já anotado no código).
* `epi_backend/mailer.py` abria SMTP **sem timeout**. O envio de cotação e de
  pedido de compra acontece com a conexão do banco aberta: um SMTP travado
  prendia a thread e uma vaga do pool indefinidamente.
* `epi_backend/db.py` tinha um **segundo** `SimpleConnectionPool`, sem
  chamadores em runtime.
* Nenhum caminho grava contexto de empresa/usuário na sessão do banco
  (`set_config`, `SET`, tabelas temporárias, `PREPARE`): o isolamento
  multi-tenant é feito em SQL por requisição. Os únicos `SET LOCAL` são do
  rollback de migração e morrem com a transação.

## 2. Correções

| Arquivo | Mudança |
|---|---|
| `core/db_pool.py` (novo) | `BoundedConnectionPool`: teto rígido (em uso + abrindo ≤ `maxconn`), espera limitada, `rollback` na devolução, descarte de conexão quebrada, ping de conexão ociosa antiga, métricas. Nenhum I/O de rede segurando a trava |
| `core/database.py` | Usa o pool novo; `connect_timeout`; `release_connection(discard=)`; `PostgresConnectionWrapper.discard()`; `db_pool_status()` com métricas |
| `app.py` | `PoolSaturatedError` → **503** `DB_POOL_SATURATED` + `Retry-After: 1` (antes: 500). `EpiHTTPServer` com fila configurável (padrão 128) |
| `epi_backend/http_utils.py` | `send_db_pool_saturated`; `send_json(headers=)` |
| `core/bootstrap.py`, `modules/data_migration/async_jobs.py` | Conexão com advisory lock de sessão preso é descartada, não reaproveitada |
| `epi_backend/mailer.py` | `SMTP_TIMEOUT_SECONDS` (padrão 30) |
| `epi_backend/db.py` | Segundo pool removido; funções delegam ao pool único |

Sem dependência nova. Sem aumento do pool: `DB_POOL_MAXCONN` continua 10.

### Configuração (todas opcionais; padrões preservam o comportamento)

| Variável | Padrão | Efeito |
|---|---|---|
| `DB_POOL_MAXCONN` | 10 | Teto (agora de fato respeitado) |
| `DB_POOL_MINCONN` | 1 | Conexões abertas na partida |
| `DB_POOL_ACQUIRE_TIMEOUT_SECONDS` | 5 | Espera por vaga antes do 503 (0 = falha imediata, como antes) |
| `DB_POOL_MAX_IDLE` | = `MINCONN` | Ociosas mantidas abertas (igual ao pool antigo) |
| `DB_POOL_PING_IDLE_SECONDS` | 30 | Ociosa mais velha que isso recebe `SELECT 1` antes da entrega |
| `DB_CONNECT_TIMEOUT_SECONDS` | 10 | Só se a `DATABASE_URL` não declarar `connect_timeout` |
| `DB_APPLICATION_NAME` | `epi-controle-pool` | Nome das sessões do pool em `pg_stat_activity` (diagnóstico) |
| `HTTP_REQUEST_QUEUE_SIZE` | 128 | Backlog do `listen` |
| `SMTP_TIMEOUT_SECONDS` | 30 | Prazo do SMTP |

### Contrato HTTP sob saturação (única mudança de contrato)

Antes: `500 {"error": "<mensagem genérica>"}`. Agora:

```
HTTP/1.1 503
Retry-After: 1
{"ok": false, "error": {"code": "DB_POOL_SATURATED", "message": "Servidor ocupado no momento. Tente novamente em instantes."}}
```

Mesmo envelope do 503 de bootstrap. O cliente web já trata 502/503/504 como
indisponibilidade temporária não fatal, com mensagem própria traduzida
(`static/js/modules/api-client.js`) — nenhum catálogo i18n muda. A
autorização não é afetada: a saturação ocorre ao pedir a conexão, antes de
qualquer leitura; não há retry no servidor.

## 3. Medições (ambiente local controlado, PostgreSQL 16)

Carga: resumo da Ficha 360° por HTTP/JWT, N clientes simultâneos × 4
requisições, empresas A e B intercaladas.

**Limite do servidor HTTP isolado** (handler sem banco):

| Backlog | N | p50 ms | p95 ms | p99 ms | falhas |
|---|---|---|---|---|---|
| 5 | 10 | 9 | 1022 | 1033 | 0 |
| 5 | 50 | 1235 | timeout | timeout | 35 de 250 |
| 128 | 10 | 10 | 12 | 12 | 0 |
| 128 | 50 | 30 | 44 | 47 | 0 |

**Antes × depois** (aplicação completa, `maxconn=10`):

| N | Antes: 5xx | Antes: p99 ms | Antes: sessões no banco | Depois: 5xx | Depois: p99 ms | Depois: sessões no banco |
|---|---|---|---|---|---|---|
| 5 | 0 | 95 | 5 | 0 | 80 | 5 |
| 10 | 0 | 1048 | 9 | 0 | 161 | 10 |
| 20 | 0 | 1359 | **12** | 0 | 376 | 10 |
| 30 | **16** | 1673 | **15** | 0 | 594 | 10 |
| 50 | **11** | 2791 | **19** | 0 | 1163 | 10 |

Em todos os níveis depois da correção: 0 respostas de outra empresa, 0
conexões retidas, 0 sessões `idle in transaction`, pico do pool = 10.

Leitura por camada: até ~10 simultâneos o limite era a **fila HTTP**; acima
disso, o **pool** (corrida + falha imediata). O **PostgreSQL** não foi o
limite em nenhum cenário. Acima de 10 simultâneos a latência cresce porque as
requisições esperam vaga — é o comportamento desejado com teto de 10.

## 4. Capacidade real (consultada, somente leitura)

* Render: 1 instância por produto, plano Free, 1 processo.
* Banco (Supabase), os dois projetos: `max_connections = 60`, 3 reservadas,
  ~6–7 sessões de plataforma em uso, `idle_in_transaction_session_timeout = 0`.
* Orçamento: 60 − 3 − ~7 ≈ 50 conexões livres para 1 instância com teto 10.
  **Não há motivo para aumentar o pool.** Se o serviço passar a ter mais
  instâncias, o teto por instância × instâncias precisa caber nesse orçamento.

Não verificado: se a `DATABASE_URL` de produção aponta para a conexão direta
ou para o pooler em modo transação. No modo transação, advisory lock de sessão
não é confiável — isso é anterior a este P0 e independe dele.

## 5. Riscos, desempenho e rollback

* **Risco:** requisições que antes falhavam em 500 imediato agora esperam até
  5 s. Se o banco estiver indisponível, threads se acumulam por até 5 s +
  `connect_timeout`. Ajustável por variável, sem deploy de código.
* **Desempenho:** custo por requisição é uma trava em memória. `SELECT 1` só
  em conexão ociosa há mais de 30 s.
* **Opcional (não aplicado):** `DB_POOL_MAX_IDLE=10` evita reabrir conexões em
  rajadas; ganho medido pequeno localmente, deve ser maior com TLS até o
  Supabase. Decisão de operação.
* **Rollback:** reverter o commit. Sem migração, sem dado novo.

## 6. Testes

* `tests/test_db_pool_p0.py` — 29 testes sem banco (teto, espera, timeout,
  rollback, descarte, ping, 503, fila HTTP, SMTP, advisory lock). Inclui um
  teste que caracteriza o defeito do `SimpleConnectionPool`.
* `tests_postgres/test_db_pool_p0_postgres.py` — 6 testes em PostgreSQL real
  via HTTP/JWT (exceção em transação, reutilização após erro,
  `pg_terminate_backend`, saturação 503, cliente que desiste, concorrência
  5/10/20/30/50 com duas empresas).

Testes locais não provam capacidade de produção. A liberação exige observar
`/api/db-pool/status` e os eventos `db.pool_saturated` no ambiente real.

## 7. P0.1 — Revisão adversarial de concorrência

Revisão do `BoundedConnectionPool` com testes determinísticos (o
entrelaçamento é forçado por eventos entre threads, sem `sleep`). Cada defeito
foi reproduzido antes da correção (`tests/test_db_pool_p0_concurrency.py`).

| # | Defeito reproduzido | Correção |
|---|---|---|
| 1 | `closeall()` enquanto `getconn()` está dentro do `connect` (fora da trava): o pool **encerrado entregava** a conexão nova | Ao voltar do `connect`, o encerramento é verificado com a trava: a conexão é fechada e `PoolError` é levantado |
| 2 | Mesma janela no ping de uma conexão ociosa | Mesmo tratamento |
| 3 | Falha no meio da abertura inicial (`minconn`) deixava as conexões já abertas órfãs | São fechadas antes de relançar |
| 4 | Duas devoluções simultâneas da mesma conexão: **dois `rollback` concorrentes** e a conexão guardada duas vezes (seria entregue a dois donos) | A posse é tomada com a trava antes da limpeza; a segunda devolução sai sem tocar na conexão |
| 5 | Devolução dupla sequencial **fechava a conexão já ociosa** no pool | Reconhecida como duplicata e ignorada |

Durante a limpeza a conexão continua contando no teto (ainda está aberta no
banco). O pool não distingue a devolução atrasada de um dono antigo depois de
a conexão ter sido reentregue; essa garantia é do `PostgresConnectionWrapper`,
que só devolve uma vez por aquisição.

### Advisory locks de sessão

`ROLLBACK` não solta advisory lock de sessão (medido em
`tests_postgres/test_db_pool_p0_postgres.py`). Os dois únicos usos — bootstrap
e job assíncrono de migração — passam por `core/session_locks.py`, que
descarta a conexão sempre que houver dúvida:

* tentativa de aquisição que levantou exceção (antes: a conexão voltava ao pool);
* saída por exceção com o lock preso;
* `pg_advisory_unlock` que levantou exceção **ou devolveu `false`** (antes: `false` era tratado como sucesso);
* dúvida anterior não é desfeita por um unlock posterior (o lock é reentrante).

Um guarda de teste reprova qualquer `pg_try_advisory_lock`/`pg_advisory_unlock`
novo fora desse acompanhamento.

### Compatibilidade com Supabase — BLOQUEIO DE CONFIGURAÇÃO antes do deploy

Documentação do Supabase (Supavisor):

* **Conexão direta** e **pooler em modo sessão (porta 5432)**: cada cliente tem
  uma sessão dedicada; advisory locks de sessão funcionam.
* **Pooler em modo transação (porta 6543)**: *não suporta* recursos de sessão
  (`SET`, `LISTEN/NOTIFY`, advisory locks). Cada transação pode cair em um
  backend diferente: o lock é adquirido num backend e o unlock chega a outro.

Efeito no modo transação: o lock de bootstrap e o de job deixam de serializar
de forma confiável e podem ficar presos num backend do pooler. A aplicação
detecta o caso (unlock devolve `false` → `db.init_lock_release_unconfirmed`) e
descarta a conexão do lado dela, mas **não consegue** soltar o lock no backend
do pooler.

O modo usado em produção **não foi confirmado**: exigiria ler a
`DATABASE_URL`, que é credencial. Consulta somente leitura a `pg_locks` nos
dois projetos não encontrou advisory lock preso no momento da revisão — o que
não prova o modo. **Antes do deploy**, o responsável deve confirmar no painel
(Render → Environment) que a `DATABASE_URL` aponta para a conexão direta ou
para o pooler na porta **5432**. Se apontar para a 6543, trocar para a 5432
(ou conexão direta) é pré-requisito para o advisory lock ser confiável; o
restante do pool funciona nos três modos.
