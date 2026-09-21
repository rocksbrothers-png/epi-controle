# R0 — de quem é o bucket: hardening da origem no `RateLimiter`

Fatia preparatória. **Não adiciona limitador novo** e **não muda limite nenhum**.
Corrige *quem* ocupa o bucket, para que qualquer limitador — os quatro que já
existem e o que virá para `/api/auth/request-email-recovery` — proteja de fato.

## 1. O defeito

```python
forwarded.split(',')[0].strip()   # o PRIMEIRO elemento
```

O primeiro elemento do `X-Forwarded-For` é **escrito pelo cliente**. Medido
antes desta fatia, com limite 3:

| | permitidos |
|---|---|
| `X-Forwarded-For` fixo | 3 / 6 — o limite funciona |
| `X-Forwarded-For` variando | **6 / 6** — o cliente escolhe o próprio bucket |

Os quatro limitadores do projeto — `login`, `recovery`, `tenant` e
`supplier_portal` — eram contornáveis com um header.

## 2. Por que não é `split(',')[-1]`

Num encadeamento onde cada proxy **acrescenta** (o `$proxy_add_x_forwarded_for`
do nginx documentado em `docs/WEB_APP_URL_ARCHITECTURE.md`), o endereço
observado pelo proxy mais interno fica na posição `-N`, com N = número de
proxies confiáveis:

```
  cliente        ->  proxy1        ->  proxy2        ->  aplicação
  manda "lixo"       acrescenta        acrescenta
                     o cliente         proxy1

  XFF na aplicação:  lixo, CLIENTE_REAL, proxy1
                           ^ posição -2, com N=2
```

`[-1]` acerta só quando N == 1. Quando N == 0 — execução local, ou aplicação
exposta diretamente — `[-1]` é o valor que o cliente mandou, e o spoof volta.

## 3. O contrato

`RATE_LIMIT_TRUSTED_PROXY_HOPS` **declara** quantos saltos confiáveis existem.
A confiança é configurada, não adivinhada.

| valor | comportamento |
|---|---|
| `0` (padrão) | ignora o cabeçalho; vale o peer do socket |
| `N ≥ 1` | usa `cadeia[-N]`; o lixo à esquerda é descartado |
| cadeia mais curta que `N` | a requisição não atravessou os proxies esperados → peer |

### Por que o padrão é 0

É o único valor seguro na ausência de configuração: sem proxy na frente, o
cabeçalho é escolha do cliente.

Uma implantação atrás de proxy que **esqueça** de declarar o valor falha
**fechando** — as origens colapsam num bucket e o excedente recebe 429 — em vez
de falhar abrindo, que é o defeito corrigido aqui. Falha fechada é barulhenta e
reversível; falha aberta é silenciosa. O gate `R0-3` existe para garantir que
esse colapso seja *consequência de má configuração*, e não o comportamento
normal.

## 4. Limitação declarada da investigação

Não consegui consultar a documentação da plataforma de produção: o proxy de
egresso deste ambiente bloqueia o domínio. **Não afirmo** quantos saltos a
Render insere, nem se ela descarta o `X-Forwarded-For` do cliente.

O desenho foi feito para **não depender** dessa resposta: a contagem de saltos
é declarada por quem implanta, e o padrão seguro cobre o caso de ninguém
declarar nada. Quando a cadeia real for confirmada, basta definir a variável —
sem tocar em código.

## 5. Concorrência — o gate que estava verde pelo motivo errado

A atomicidade do `is_allowed` já existia (lock único cobrindo poda, checagem e
append) e foi preservada. Mas o gate que a media **não media nada**: removendo
o lock, ele acusou em **0 de 5 execuções**, porque a seção crítica é curta o
bastante para o GIL serializá-la por acidente.

Duas correções, e a primeira também estava errada:

1. Instrumentei o dicionário de janelas para ceder o turno — **antes da
   leitura**. Continuou 0/5: atrasar o lugar errado não reproduz a corrida.
2. Movi a cessão para depois da leitura do tamanho, dentro de `__len__`. É isso
   que carrega um valor **velho** através da troca de contexto, que é a corrida
   real. Passou a acusar **5/5**.

Ficaram dois gates com modos de falha diferentes: o comportamental (`R0-6b`),
que depende de escalonamento, e o estrutural (`R0-6c`), que não depende de
sorte nenhuma.

Nada disso alterou o produto — a instrumentação vive só no teste.

## 6. Sabotagens

| Sabotagem | Acusada por |
|---|---|
| α — volta a confiar no primeiro elemento do XFF | 8 gates |
| β — XFF arbitrário muda bucket sem proxy confiável | 7 gates |
| γ — fallback sem proxy quebrado | `R0-3`, `R0-4`, `R0-5c` |
| δ — atomicidade removida | `R0-6b`, `R0-6c` |

## 7. Limites: inalterados

| Limiter | Limite |
|---|---|
| `login_limiter` | 10 / 60 s |
| `recovery_limiter` | 5 / 300 s |
| `tenant_limiter` | 60 / 60 s |
| `supplier_portal_limiter` | 30 / 60 s |

Gate `R0-7..10` trava os quatro. A finalidade desta fatia é *quem* ocupa o
bucket, não *quantas* requisições ele aceita.

## 8. Adaptação necessária

`tests/test_recovery_sem_enumeracao.py` isolava buckets variando o
`X-Forwarded-For`. Como o cabeçalho deixou de decidir origem, o harness passou
a variar o **peer do socket** — que é o que o produto honra agora. Um harness
que continuasse variando o header estaria exercitando um caminho que não existe
mais.

## 9. Fora do escopo

`/api/auth/request-email-recovery`, throttle de e-mail e os números dos limites
continuam para a R1. A dívida de deployment (gunicorn duplicado, pins
conflitantes, `spec/09-deployment.md` descrevendo `app:application`, que não
existe) foi registrada em issue separada.
