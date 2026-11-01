# SECURITY-CSP-REPORT-REDACTION-V1 — relatórios de CSP sem tokens no log

Projeto: **Corporate** (`rocksbrothers-png/epi-controle`). Base: `main` `13a1e8bf`.

## 1. Causa

`/api/csp-report` (`app.py`, `_handle_csp_report`) recebe os relatórios de violação que o navegador envia pelo
`report-uri`. Ele gravava em `security.csp_report` os campos `document-uri`, `blocked-uri` e `source-file` **como
vieram**, cortados em 240 caracteres.

Essas URLs carregam o endereço completo da página e do recurso:
- o link do portal do colaborador (`/?employee_token=…`);
- o portal do fornecedor (`/fornecedor/<token>`, `/api/portal/supplier/<token>`);
- qualquer query de terceiros (`?token=`, `?code=`);
- credenciais embutidas (`https://usuário:senha@host`).

Na reprodução, um `employee_token` fictício foi parar em claro no log, e o endpoint aceitou 200 relatórios em 1,2 s.
A falta de redação já existia em produção, mas a política estrita da CSP-V1 aumenta o volume de relatórios, inclusive
os gerados por extensões de navegador na página do portal.

## 2. Correção

- **`core/csp_report.py`** (novo, funções puras):
  - **Campos de URL:** `document-uri`/`documentURL`, `blocked-uri`/`blockedURL`, `source-file`/`sourceFile` e
    `referrer`. Ficam só a origem e o caminho:
    - query e fragmento são **descartados por inteiro**, restando só o marcador `?…`/`#…`. Assim nenhum parâmetro
      precisa constar numa lista para não vazar;
    - usuário e senha embutidos são removidos;
    - o segmento após `/fornecedor/` e `/api/portal/supplier/` vira `***`, assim como qualquer segmento com 20 ou mais
      caracteres de token (urlsafe, hex ou `%`);
    - `data:` fica só com o esquema e `blob:` só com esquema e origem;
    - palavras-chave da CSP (`inline`, `eval`, …) passam como estão;
    - URL inválida vira `[inválido]`, sem ecoar o valor;
    - o resultado é limitado a 240 caracteres.
  - **Campos que não são URL** só passam com o formato esperado:
    - diretiva: `[a-z][a-z0-9-]*`, só o nome;
    - números inteiros;
    - disposição: `enforce` ou `report`.
  - **`script-sample`/`sample` e `original-policy` nunca são registrados.**
  - **Formatos aceitos:**
    - `{"csp-report": {...}}` (`application/csp-report`);
    - o mesmo objeto sem envelope;
    - Reporting API (`application/reports+json`), até 10 itens por requisição, só os do tipo `csp-violation`.
  - **Exceções:** qualquer erro de leitura ou de parse resulta em lista vazia. Nenhuma mensagem de exceção leva o
    conteúdo recebido.
- **`app.py`:** `_handle_csp_report` registra só os campos sanitizados. Fica igual:
  - o limite de **64 KiB** do corpo;
  - a resposta 204 sem conteúdo;
  - a ausência de autenticação, que é necessária;
  - a execução antes da barreira de bootstrap, sem depender do banco.
- **Abuso:** `core/csp_report.py` instancia `csp_report_limiter` (com a classe `RateLimiter` existente; o
  `core/rate_limit.py` tem digesto fixado e não muda), com 120 relatórios por minuto por chave de origem; o
  excedente recebe 429, sem log.
  - Atrás do proxy, com `TRUSTED_PROXY_HOPS=0`, a chave é o IP do proxy, e o limite funciona como teto global contra
    inundação de log.
  - Relatórios legítimos são poucos por página.

## 3. Testes

| Teste | Resultado |
|---|---|
| `tests/test_security_csp_report_redaction_v1.py` (40) | 40/40 passaram |
| ↳ sanitização: query, fragmento, credenciais, tokens no caminho (fornecedor e API), segmentos longos, `data:`/`blob:`, palavras-chave, IPv6, porta inválida, entradas hostis | coberta |
| ↳ formatos: `csp-report`, objeto sem envelope, Reporting API (com limite de itens e filtro por tipo) | coberta |
| ↳ dados malformados ou ausentes: vazio, `null`, número, texto, aninhamento excessivo, UTF-8 inválido, envelope não-objeto | coberta |
| ↳ HTTP real contra o `EpiHandler`: o log tem só campos sanitizados e nenhum dos 7 valores fictícios; Reporting API; malformado; limite de 64 KiB; 429 acima do limite; não depende do bootstrap | coberta |
| Mesmos testes HTTP contra o `app.py` da `main` | **4 falham**: token no log, Reporting API ignorada, registro vazio para JSON inválido, sem 429 |
| Ponto de entrada real (`server_postgres.py`) com PostgreSQL local e `CSP_MODE=report-only` | 7 tokens fictícios: 0 ocorrências no log; relatórios legítimos registrados; rajada de 150 → 116 × 204 e 34 × 429; `/health` 200 |
| Chromium real: violação disparada numa página com `?employee_token=`, enviada pelo `report-uri` | registrado `document_uri=http://127.0.0.1:18111/?…`, `blocked_uri=inline`, diretiva, linha, coluna e `disposition=report`; token: 0 ocorrências |

## 4. Avaliação de segurança

- **O que melhorou:**
  - tokens e credenciais de URL não chegam mais ao log, venham na query, no fragmento, no caminho dos portais ou
    embutidos na URL;
  - o conteúdo das amostras de script nunca é registrado;
  - campos livres não permitem injeção de texto no log;
  - há um teto de volume.
- **O que se perde de diagnóstico:** a query e o fragmento das URLs. Origem, caminho, diretiva, linha, coluna e
  disposição continuam disponíveis, e isso basta para localizar a violação.
- **Riscos residuais:**
  - um token que apareça no caminho com menos de 20 caracteres, fora das rotas conhecidas, passaria. Hoje não existe
    rota assim;
  - o limitador é em memória, por instância;
  - o log da Render continua sendo o destino. O acesso a ele deve seguir restrito.
