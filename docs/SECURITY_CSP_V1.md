# SECURITY-CSP-V1 — Content Security Policy aplicada na SPA

Base: Corporate `55f7c11f` / SaaS `f1299e6` (já com SECURITY-OUTPUT-XSS-V2).
Objetivo: passar a CSP de Report-Only para uma política efetivamente aplicada, sem interromper funcionalidades
legítimas, e sem ligar política restritiva em produção antes de validar o impacto.

## 1. Inventário (antes)

**Cabeçalho:** um único `Content-Security-Policy-Report-Only`, igual para todas as respostas (`app.py`):

| Diretiva | Fontes |
|---|---|
| `default-src` | `'self'` |
| `script-src` | `'self' 'unsafe-inline' https://unpkg.com https://sdk.mercadopago.com` |
| `style-src` | `'self' 'unsafe-inline' https://fonts.googleapis.com` |
| `img-src` | `'self' data: blob: https://api.qrserver.com` |
| `font-src` | `'self' data: https://fonts.gstatic.com` |
| `connect-src` | `'self' https://api.mercadopago.com` |
| `frame-ancestors`, `base-uri` | `'self'` |

Ausentes: `object-src`, `form-action`, `worker-src`, `media-src`. Rotas com política própria e aplicada: ficha HTML
(`FICHA_HTML_CSP`, script de impressão por hash) e arquivos da Biblioteca (`default-src 'none'`).

**Recursos que a SPA usa:**

| Tipo | O que existe |
|---|---|
| Script inline | 1 bloco: pré-paint do tema (`views/_head.html`) |
| Handler inline | 1 no HTML (`onsubmit="return false"` do login) e 11 em templates JS: fornecedores autorizados (5) e botão de fornecedor da PO (1) no `app.js`, cotações (5) no `procurement.js` |
| Script externo | htmx (`unpkg.com`, com SRI); sob demanda: html5-qrcode e ZXing (`unpkg.com`), SheetJS (`cdn.jsdelivr.net`) |
| `eval`, `new Function`, `setTimeout` com string, `javascript:` | nenhum |
| Estilo | folhas próprias, Google Fonts, 467 atributos `style=` no HTML e muitos nos templates |
| Imagem | logotipos, fotos de EPI e assinaturas em `data:`; QR code de `api.qrserver.com`; `blob:` |
| Conexão | só a própria origem (`/api/...`), nos dois projetos |
| Câmera | `getUserMedia` + bibliotecas de leitura (QR/código de barras) |
| Popups de impressão | `window.open` + `document.write` (herdam a CSP da página; só estilo inline, sem script) |
| Frames | nenhum |

**Outras superfícies:**
- **Portal do colaborador:** parte da própria SPA (`?employee_token=`), mesma política.
- **Portal do fornecedor** (`/fornecedor/<token>`): página autocontida com um `<script>` embutido.
- **Checkout** (`/pagamento`, `/checkout`, `pagamento.html`): SDK do Mercado Pago (scripts, frames e conexões de
  vários domínios).
- **Flutter Web** (`/app/`): o Corporate serve o build em `static/app`; o SaaS publica o Flutter separadamente
  (outra origem para a API, Firebase). O SDK do Flutter não está disponível neste ambiente.

## 2. Problemas encontrados

1. **A política estrita quebraria o app sem mudanças no frontend.** Verificado no Chromium com a política aplicada
   sobre a `main`:
   - o pré-paint é bloqueado e o tema escuro da sessão se perde;
   - o `onsubmit` do login é bloqueado;
   - o botão "Editar" de fornecedor fica sem efeito (o mesmo vale para os outros 10 `onclick`).
2. **XSS em contexto de JavaScript.** Dois botões de fornecedor punham o nome dentro de um literal JS no atributo:
   `onclick="toggleSupplierActive(id, '${esc(s.name)}', …)"`. O navegador decodifica as entidades antes de rodar o
   handler, então um nome com `'` (como `O'Brien`) quebrava o botão, e um nome malicioso executava código.
   `esc()` não protege esse contexto.
3. **Empilhar CSPs quebra a ficha.** Duas CSPs aplicadas valem pela interseção. Se a CSP da SPA fosse somada à da
   ficha, o script de impressão (liberado só pelo hash) seria bloqueado.

## 3. Correção

### Frontend (sem script inline nem handler inline)
- **Pré-paint:** passou para `static/js/boot/theme-preference.js`, carregado de forma síncrona no mesmo ponto do
  `<head>` (aplica o tema antes do primeiro paint). O mesmo arquivo bloqueia o envio nativo do `#login-form` até o app
  carregar, o que antes fazia o `onsubmit` inline.
- **Fornecedores autorizados:** os botões levam `data-supplier-action` e `data-supplier-id`, tratados por um único
  listener delegado. O fornecedor é buscado na lista carregada, e o nome não passa mais por literal JS.
- **Cotações** (`procurement.js`): `data-quote-action` e `data-quote-id`, com listener delegado no módulo.
- **Botão de fornecedor da PO:** `data-po-supplier-actions`, tratado pelo listener existente de `compras-po-tbody`
  (`purchases.js`).

### Backend
- **`core/csp.py`:** políticas por superfície.

  | Superfície | Cabeçalho | Política |
  |---|---|---|
  | SPA (todo o resto) | conforme `CSP_MODE` | `script-src 'self'` + as 4 bibliotecas pelo **URL exato**; `object-src 'none'`; `form-action 'self'`; `connect-src 'self'`; `img-src 'self' data: blob: https://api.qrserver.com`; `media-src`/`worker-src 'self' blob:`; `frame-ancestors 'self'`; `base-uri 'self'` |
  | Flutter Web (`/app/`, `/flutter_web/`) | sempre Report-Only | `'wasm-unsafe-eval'` (CanvasKit), `https://www.gstatic.com`, `connect-src 'self' https:` |
  | Checkout (`/pagamento`, `/checkout`, `/pagamento.html`) | sempre Report-Only | domínios do Mercado Pago (scripts, frames, conexões) |
  | Portal do fornecedor | aplicada, da rota | `default-src 'none'`; `script-src` só o **hash** do script embutido; `connect-src 'self'`; `frame-ancestors 'none'` |
  | Ficha, Biblioteca | aplicada, da rota (sem mudança) | — |

  Nenhuma política da SPA tem `'unsafe-inline'` ou `'unsafe-eval'` em `script-src`, nem host inteiro de CDN.
- **`CSP_MODE`** (`enforce` | `report-only`):
  - padrão `enforce` fora de produção e `report-only` em produção;
  - a política é a mesma nos dois modos, então produção passa a reportar exatamente o que seria bloqueado;
  - valor inválido cai no padrão.
- **`app.py`:**
  - `send_header` registra quando a rota já mandou `Content-Security-Policy`, e a CSP da SPA não é somada;
  - o registro é zerado a cada resposta;
  - a Biblioteca segue só com a sua política.
- **`report-uri`:** continua vindo de `CSP_REPORT_URI`. Agora também recusa espaço e `;`, que injetariam diretivas.
- **`scripts/check_web_hardening.py`:** exige no `index.html` nenhum `<script>` inline e nenhum handler `on*=`, e na
  política da SPA nenhum `'unsafe-inline'`, `'unsafe-eval'`, `*`, `https:` ou `http:` em `script-src`.

**Sem mudança em:** dados gravados, rotas, RBAC, regras de negócio e textos de interface (5 idiomas).

## 4. Testes

| Teste | Resultado |
|---|---|
| `tests/test_security_csp_v1.py` (37): política estrita; URLs exatos batem com o que o frontend carrega; padrões de `CSP_MODE`; Flutter/checkout Report-Only; rota com CSP própria não recebe a da SPA (ficha, Biblioteca); registro zerado por resposta; `report-uri` só quando seguro; hash do portal do fornecedor; nenhum handler inline em `static/` (guarda + autoteste); `index.html` sem script inline | 37/37 |
| `scripts/browser/security_csp_v1.py` (Chromium, API sintética, CSP aplicada, 5 idiomas) | 5/5 idiomas, 0 violações |
| `scripts/browser/security_csp_v1_realflow.py` (Chromium + `app.py` + PostgreSQL local descartável, 5 idiomas) | 5/5, 19 telas, 0 violações |
| Negativos (abaixo) | 6/6 cenários |
| JS (`static/js/test/run-tests.js`) | 665 |
| Guarda UBX, `check_web_hardening.py`, `build_index.py check` | OK |

**Harness com API sintética.** O servidor estático manda o mesmo cabeçalho do `app.py`. Em cada idioma:
- **Login:** o pré-paint externo aplica o tema da sessão, e o login real envia por `handleLogin`, sem a senha na URL.
- **Telas:** as 12 telas e todas as abas (37 visitas), mais os renderizadores pontuais: fichas, relatórios,
  estoque, compras, entregas, usuários e configuração.
- **Ações que eram `onclick` inline:**
  - editar, suspender, POs, catálogo e integração do fornecedor;
  - e-mail, portal, API, resposta e vencedora da cotação;
  - fornecedor da PO.

  O nome `Forn O'Brien "Ltda"` chega íntegro às funções.
- **Imagens:** logotipo, foto do EPI e assinatura desenhada no modal real e exibida carregam, assim como o QR code.
- **Bibliotecas sob demanda:** html5-qrcode, ZXing e SheetJS carregam (pelo caminho real de importação de `.xlsx`).
- **Portais:** o portal do colaborador (tela de validação) e o do fornecedor (o script embutido roda e mostra a
  cotação).
- **Ficha:** com a política da ficha, mostra logotipo e assinatura e roda só o script de impressão.

**Negativos:** script inline, `onerror`, `onclick`, script externo não autorizado, `setTimeout` com string, `eval` e
`javascript:`.

| Modo | SPA | Portal do fornecedor |
|---|---|---|
| CSP aplicada | nada executa, 7 violações; o script externo nem é requisitado | nada executa, 7 violações |
| Sem CSP (controle: o teste detecta) | as 6 injeções executam | as 6 executam |
| Report-Only (padrão de produção) | executam e geram 8 relatórios | nada executa (a política da rota é sempre aplicada) |

**Fluxo real (`app.py`).** Há uma única CSP por resposta:
- `/` e `/index.html`: aplicada, sem `'unsafe-inline'` em `script-src`;
- `/app/` e `/pagamento`: Report-Only;
- `/fornecedor/<token>`: só a política da rota.

Em cada idioma: login pelo formulário, troca de idioma e navegação por 19 telas, com 0 violações.

### Corporate e SaaS

O código da CSP (`core/csp.py`, `app.py`, portal do fornecedor e frontend) é o mesmo nos dois projetos. Os resultados
foram os mesmos nos dois:
- testes unitários;
- harness com API sintética: 5/5 idiomas e 6/6 negativos;
- fluxo real com `app.py` + PostgreSQL local: 5/5 idiomas e 19 telas;
- 665 testes JS;
- pytest completo, com só a falha ODS preexistente.

No SaaS, `scripts/check_web_hardening.py` já falhava na `main` (`f1299e6`): o Dockerfile do SaaS não empacota o
Flutter (`./static/app/`), que é publicado à parte. As verificações novas da CSP rodam antes desse ponto e passam. O
script não faz parte do CI.

## 5. Implantação (não feita por esta demanda)

1. Publicar com o padrão. Em produção, a SPA fica em **Report-Only**, com a política estrita. Configurar
   `CSP_REPORT_URI=/api/csp-report`: o endpoint já existe e registra `security.csp_report` no log.
2. Acompanhar os relatórios em uso real (perfis, idiomas, câmera, importação de planilha, impressão).
3. Sem violações legítimas, definir `CSP_MODE=enforce` em produção. O rollback é voltar a variável, sem deploy de
   código.

## 6. Riscos residuais

- **`style-src 'unsafe-inline'`:** centenas de atributos `style=` no HTML e nos templates. Nonce e hash não cobrem
  atributos. Injeção de CSS não executa script, mas ainda permite alterar o visual e alguns vazamentos por seletor.
  Remover exige migrar os estilos para classes (demanda própria).
- **Flutter Web e checkout continuam em Report-Only:**
  - O build do Flutter não pôde ser gerado nem testado aqui (o SDK não está disponível), e o SaaS publica o Flutter
    em outra origem. O `index.html` do Flutter tem um script inline que precisa de hash.
  - O SDK do Mercado Pago só pode ser validado com o serviço real.
- **SheetJS sem versão fixa:** `https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js` (sem versão nem SRI). A CSP
  libera esse URL exato, mas o conteúdo pode mudar no CDN. Recomendado fixar a versão ou servir localmente.
- **Bibliotecas externas em CDN público** (htmx, html5-qrcode, ZXing): liberadas pelo URL exato, e o htmx tem SRI.
  Hospedá-las na própria origem eliminaria a dependência de terceiros.
- **Handlers atribuídos por JS** (`el.onclick = …`) e `addEventListener` não são afetados pela CSP e seguem
  funcionando. A guarda impede apenas o retorno de handlers inline em HTML.

## 7. Pendências registradas (sem alteração de dados)

Mantidas como registro, conforme a autorização:

- **Usuários Master sem registro no histórico empresarial:** a trilha é por empresa (FIX-USERS-ACTIVE-V1).
- **Contas possivelmente reativadas antes da FIX-USERS-ACTIVE-V1:** continuam ativas. Identificá-las exige cruzar
  logs. Nenhum dado foi alterado.
- **Criação de usuário com `active=0` ignorado:** comportamento anterior; o formulário não oferece a opção.
- **Falha preexistente do teste ODS** (`test_migration_phase2_formats[ods]`): `No module named 'odf'` localmente.
  Também falha na `main` dos dois projetos; no CI, que instala a dependência, passa.
- **Módulos fora da revisão XSS (V1/V2):** avaliações de EPI, Biblioteca de Segurança, migração e portais (do
  colaborador e do fornecedor).
  - Não fazem parte da varredura de texto contaminado.
  - Esta demanda cobre esses módulos só quanto à CSP: as telas abrem sem violação e o portal do fornecedor passou a
    ter política com hash.
  - A CSP reduz o impacto de um escape que falte, mas não substitui a revisão de saída dessas telas.
