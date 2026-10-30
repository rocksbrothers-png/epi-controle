# SECURITY-OUTPUT-XSS-V1 — dados de cadastro renderizados como HTML

Base: Corporate `776d516d` / SaaS `df453a5`. Os arquivos alterados são idênticos nos dois repositórios.
Continuação de SECURITY-LOGO-XSS-V1 (`docs/SECURITY_LOGO_XSS_V1.md`), que listou estes pontos como risco residual.

## 1. Gravidade

**Alta.** XSS armazenado: texto de cadastro chega a `innerHTML` (SPA) ou a um HTML servido na mesma origem (ficha)
sem escape.

| Origem | Quem grava | Onde executava | Escalada |
|---|---|---|---|
| Nome/CNPJ da empresa | Administrador Geral (Minha Empresa) ou Master | Topo do app, selects de todo cadastro, filtros, Comercial, Empresas, usuários | Administrador Geral → Administrador Master |
| Nome/fabricante/foto do EPI | Administrador de cadastro | Lista e cadastro de EPI, busca de EPI em Entrega/Estoque, selects | Dentro da empresa; e o Master que abre a tela |
| Campos da ficha (colaborador, EPI, CA, unidade, empregador, devolução, configuração da ficha) e assinatura | Cadastro, entrega, devolução, configuração | Ficha EPI em HTML (`/api/ficha-epi/*.html`, `/api/ficha-epi-period/*.html`, `/api/ficha-archive/*.html`) | Quem abre a ficha (inclusive o Master); o snapshot guarda o HTML |
| Histórico Comercial (resumo, responsável, detalhes) | Ações dos administradores | Cards, filtro, impressão (`document.write` em popup da mesma origem) e exportação | — |

O CSP do app está em modo *Report-Only*, então não bloqueia nada.

## 2. Reprodução (Chromium, `main` `776d516d`)

`scripts/browser/security_output_xss.py`, com `<img src=x onerror=…>` como nome e CNPJ de empresa, nome, fabricante e
foto de EPI, e no resumo e responsável do histórico. Em pt-BR, os quatro cenários maliciosos executam script em:

- **topo:** `#company-badge`;
- **select de empresa:** `#employee-company`;
- **Comercial:** `#commercial-summary`, `#commercial-alerts`, `#commercial-history`, `#commercial-company`;
- **Empresas:** `#companies-table`, `#company-details`;
- **EPI:** `#approved-epi-table` (nome, fabricante e foto).

As demais telas corrigidas (usuários, colaboradores, unidades, relatórios, estoque, arquivamento, dashboard, demandas
de compra, busca de EPI) usam o mesmo padrão de template e são cobertas pelos testes JS e pela guarda de código
(item 4), não por cenário de navegador.

Ficha HTML renderizada pelo código da `main` e servida como a `main` serve (sem CSP): **16 campos executam script**:

- **colaborador:** nome, função, setor, empresa de origem;
- **empregador:** CNPJ;
- **unidade e período:** unidade, período;
- **configuração da ficha:** título, declaração, observações, rodapé;
- **entrega:** EPI, CA, assinatura;
- **devolução:** EPI, motivo.

## 3. Correção

### A. Ficha EPI em HTML (`modules/ficha/service.py`, `modules/ficha/routes.py`)

- Todo dado de registro passa por `_esc` (`html.escape`), inclusive título, declaração, observações e rodapé da
  configuração. As quebras de linha continuam virando `<br>` depois do escape.
- Assinatura e logotipo só entram como data URL base64 de imagem (`safe_image_data_url`) e escapados. Assinatura em
  outro formato (ex.: código/token) não vira imagem, como antes.
- **CSP nas três rotas da ficha.** Inclui o snapshot gravado antes desta correção, que não é reescrito:

  ```
  default-src 'none'; img-src data:; style-src 'unsafe-inline';
  script-src 'sha256-…'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'
  ```

  - O único script permitido é o de impressão do arquivo, liberado pelo hash (gerado do mesmo texto que a rota injeta).
  - Handlers inline (`onerror`, …) e qualquer outro script ficam bloqueados.
  - A impressão a partir da tela (`popup.print()` chamado pelo app) continua funcionando: é a página de origem que
    chama, e o CSP não usa `sandbox`.
- **Arquivo exportado** (`snapshot_export`): o download não leva o cabeçalho, então o mesmo CSP (sem
  `frame-ancestors`, que não vale em `<meta>`) é inserido como `<meta http-equiv>` logo após `<head>`, antes de
  qualquer dado do snapshot.
- Texto sem `& < > " '` sai idêntico; com esses caracteres, o visual é o mesmo e o HTML usa a entidade (o
  `html_sha256` de snapshots **novos** com esses caracteres muda; snapshots existentes não são alterados).

### B. Foto do EPI

- **Gravação** (`modules/epis/service.py`, `validate_epi_photo_payload`):
  - só é aceita uma data URL base64 de imagem (qualquer subtipo `image/*`, como o upload aceita);
  - valor vazio limpa a foto; valor novo fora da regra é recusado;
  - a foto já gravada que o formulário reenvia segue como está, para não bloquear a edição (a exibição a ignora).
- **Exibição:**
  - `views/epis.js` (lista) e `epi-registration.js` (prévia) mostram `<img>` só para data URL base64 de imagem e
    escapam todas as colunas;
  - `buildEpiRow` (tabela do cadastro) escapa todas as colunas.
- **Biblioteca de segurança:** a rota da foto já aceitava só PNG/JPEG e reencodava com Pillow. Não mudou.

### C. Assinaturas

- O único ponto em que a assinatura vira HTML é a ficha (item A). A SPA não renderiza `signature_data`.
- **Sem mudança no armazenamento, na validação ao gravar ou na evidência** (`deliveries/evidence.py` usa o conteúdo
  da assinatura): validade jurídica e registros existentes intocados, conforme a autorização.

### D. Nomes de empresa e CNPJ (e textos vizinhos)

- **Topo do app:** nome e CNPJ escapados.
- **Comercial:**
  - cards de resumo, alerta e vencimento: nome, plano e motivos escapados;
  - select de empresa e filtro de responsável escapados;
  - histórico: nome, ação, responsável, resumo e detalhes escapados;
  - impressão e exportação do histórico escapadas.
- **Empresas** (`companies-view.js`): nome, razão social, CNPJ, plano e observações escapados.
- **Helpers centrais:**
  - `populateSelect`: selects de empresa, unidade, colaborador e EPI em todos os cadastros;
  - `populateSearchSelect`: filtros de empresa e unidade de 9 telas;
  - select de EPI da entrega/estoque;
  - busca de EPI em Entrega/Estoque.
- **Outros pontos com nome de empresa** (todos os `innerHTML` com `company_name`, encontrados na auditoria
  independente e numa varredura completa):
  - colaboradores (lista e seleção), unidades, relatórios, estoque mínimo, arquivamento de colaboradores e de
    unidades, dashboard (últimas entregas), relatório de entregas e demandas de compra (coluna do Master);
  - filtro e tabela de usuários (nome do usuário também escapado);
  - select de empresa da configuração da ficha;
  - filtro de empresa com CNPJ;
  - tela da ficha na SPA (`fichas.js`): empresa, CNPJ, colaborador, setor, função, unidade. O fallback do escape
    nunca devolve texto cru.

Sem mudança em RBAC, rotas, permissões, isolamento multiempresa, regras de negócio ou dados gravados.

## 4. Testes

| Teste | `main` | Com a correção |
|---|---|---|
| `tests/test_security_output_xss_v1.py` (45): todos os campos da ficha; assinatura maliciosa/não-imagem; dados legítimos (logotipo, assinatura, `<br>`, texto); CSP (hash do script de impressão, sem `unsafe-inline`); CSP enviado nas três rotas e dentro do arquivo exportado; foto de EPI (positivos, negativos, legado) | não importa (helper inexistente) | 45 passam |
| `tests/test_security_output_xss_v1_company_sinks.py`: guarda que falha se algum template de `static/` interpolar `company_name` cru logo após uma tag | 10 pontos crus | 0 |
| `scripts/browser/security_output_xss.py` (Chromium, 5 idiomas, 9 cenários): topo e selects, Comercial, Empresas, EPIs (malicioso e legítimo, foto legítima carrega) e ficha HTML com CSP (render atual + snapshot antigo; impressão do arquivo roda) | maliciosos executam em todas as telas; ficha: 16 campos | 45/45, nada executa |
| Caracterização UBX: `epis-registration-runtime.js` (mocks de foto passam a ser data URLs válidas; o teste do escape passa a exigir que valor malicioso não vire `<img>`) e a referência congelada de Empresas (mesmo escape, comentado) | — | 659 testes JS |

Isolamento multiempresa: nenhuma consulta, rota ou permissão mudou. As suítes existentes de escopo
(`tests/test_employee_visibility_scope.py`, `tests_postgres/*multi*`, `*escopo*`) continuam passando no CI.

## 5. Riscos residuais (fora deste PR)

- **Texto de cadastro sem escape em outras telas (sistêmico).** Restam cerca de 188 interpolações `${item.campo}` em
  `innerHTML` (contagem heurística; parte é número/id). Exemplos:
  - nomes de colaborador, de unidade e de EPI em `employees-view.js`, `archival-view.js`, `estoque.js`,
    `reports-view.js`, dashboard e relatórios (o nome da **empresa** já está escapado em todas as telas, com guarda).

  Proposta: **SECURITY-OUTPUT-XSS-V2**, varredura sistemática com regra de lint/guarda que proíba interpolação crua
  em `innerHTML`.
- **CSP do app em Report-Only** (ver proposta SECURITY-CSP-V1). A ficha já tem CSP aplicado.
- **Valores maliciosos já gravados** (nomes, fotos) continuam no banco. Não são mais executados nos pontos
  corrigidos; a limpeza exigiria autorização.
- **Tamanho da foto do EPI:** sem limite de tamanho ao gravar (anterior a esta correção; a biblioteca de segurança
  limita a 8 MB). Proposta junto com V2.
- **Assinaturas:** a gravação aceita qualquer texto. A exibição está protegida. Validar o formato ao gravar exige
  decisão (possível impacto em fluxos/evidência).
