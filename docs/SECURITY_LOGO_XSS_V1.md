# SECURITY-LOGO-XSS-V1 — XSS armazenado via logotipo da empresa

Base: Corporate `c1c9ac6f` / SaaS `b936120a` (os arquivos alterados são idênticos nos dois repositórios).
Origem do achado: CodeQL "DOM text reinterpreted as HTML" nos PRs da UBX-V5 (fatia Minha Empresa), em código só
movido; a falha já existia na `main`.

## 1. Gravidade

**Alta.** XSS armazenado com escalada entre empresas:

- **Quem grava:** o Administrador Geral da própria empresa (`company_settings:update`, via `PUT /api/my-company`)
  ou o Administrador Master (Empresas, suporte e marca da plataforma).
- **Onde executa:**
  - para os usuários da empresa: topo do app e ficha;
  - para o Administrador Master: lista e detalhes de Empresas e painel Comercial;
  - para qualquer visitante, sem login: tela de login do domínio/slug da empresa.
- **Mitigação existente:** nenhuma efetiva. O CSP do app está em modo *Report-Only*. A ficha HTML é servida na mesma
  origem, sem CSP.

## 2. Origem, fluxo e pontos de execução

**Origem.** `logo_type`, `login_logo_type` e `favicon_type` em `companies`, e `logo_type`/`login_logo_type` da marca
da plataforma. Todos guardam uma data URL.

**Validação ao gravar (antes).** `validate_logo_payload` (`modules/commercial/service.py`):
- só conferia o prefixo `data:image/png|jpeg|jpg|svg+xml`;
- aceitava qualquer outro texto que não começasse com `data:image/`, incluindo `data:text/html`.

`validate_login_logo_payload` também só conferia o prefixo. `favicon_type` no white-label de Empresas não tinha
validação nenhuma. Na prática, a `main` aceitava 11 das 12 entradas maliciosas do teste.

**Pontos de execução.** O valor era inserido sem escape em atributos `src`:

| Ponto | Arquivo | Condição antiga |
|---|---|---|
| `companyLogoSrc`/`companyLogoMarkup` (topo, Empresas, Comercial, marca da plataforma, prévias de Minha Empresa e da marca, ficha na SPA) | `static/app.js` | `startsWith('data:image/')`; o nome da empresa também entrava sem escape no `alt` |
| Tela de login pública | `static/tenant-init.js` (`applyBranding`) | `startsWith('data:')` |
| Ficha EPI em HTML (servida como `text/html` na mesma origem e guardada em snapshot) | `modules/ficha/service.py` | `startswith('data:image')` |

**Reprodução no Chromium (`main`).** Usei `data:image/png;base64,AAAA" onerror="…"` e um nome de empresa com
`" onload="…"`. O script executou nos 4 pontos testados: login, topo, Empresas e Minha Empresa.

## 3. Correção (causa e pontos de execução)

1. **Gravação (causa).** Só passa uma data URL **base64** de tipo permitido:
   `^data:image/(png|jpeg|jpg|svg+xml);base64,[A-Za-z0-9+/]+={0,2}$`.
   - O alfabeto base64 não tem aspas, espaços nem `<`/`>`, então o valor não fecha o atributo nem abre elemento.
   - Logotipo e favicon aceitam PNG/JPEG/SVG; o logotipo de login aceita PNG/SVG, como antes.
   - `favicon_type` no white-label de Empresas passa a usar a mesma validação de Minha Empresa.
   - Texto legado sem `data:` (que o app nunca mostrou como imagem; mostrava o logotipo padrão) é descartado ao
     gravar, em vez de recusado.
   - No cadastro de Empresas, as imagens do white-label são validadas fora do `try/except` que engolia erros
     (achado da auditoria: antes o valor bruto chegava ao `INSERT`).
   - **Valor já gravado reenviado não bloqueia a gravação.** As telas reenviam a imagem atual com os demais campos
     (`companySavePayload`, ativar/inativar, Comercial, Minha Empresa, marca da plataforma). Uma data URL gravada
     antes da regra estrita poderia impedir o Master de editar ou suspender a empresa, ou o Administrador Geral de
     salvar as configurações. Por isso:
     - na edição de Empresas, as imagens são campos protegidos que a rota restaura do registro atual; o valor
       reenviado só é saneado, sem recusa;
     - em Minha Empresa e na marca da plataforma, se o valor enviado é igual ao gravado, ele é mantido como está (a
       exibição já o ignora); um valor novo continua sujeito à regra estrita.
2. **Leitura pública.** `/api/tenant/resolve` (sem login) devolve vazio para valores gravados antes da correção que
   não passem na regra.
3. **Exibição (defesa em profundidade, cobre dados já gravados).**
   - `companyLogoSrc` usa a mesma regra; qualquer outro valor mostra o logotipo padrão.
   - `companyLogoMarkup` escapa `class`, `src` e o nome da empresa no `alt`.
   - `tenant-init.js` usa a mesma regra e escapa o `src`.
   - A ficha HTML usa a mesma regra, `html.escape` no `src` e escapa o nome da empresa no bloco do logotipo.

**Logotipos legítimos.** Continuam iguais: os uploads do app geram sempre data URL base64 (`FileReader.readAsDataURL`
e `canvas.toDataURL`). Para um logotipo válido, o HTML gerado é idêntico ao anterior.

**O que não muda.** RBAC, rotas, permissões e isolamento multiempresa. Também não houve nenhuma alteração nas regras
de CodeQL nem exclusões.

## 4. Testes

| Teste | Cobre | Na `main` | Com a correção |
|---|---|---|---|
| `tests/test_security_logo_xss_v1.py` (75) | Validação de logotipo, login e favicon; marca da plataforma; Minha Empresa; white-label; cadastro e edição de Empresas; valor legado reenviado; resolução pública de tenant; ficha HTML. Negativos (12 entradas maliciosas) e positivos (PNG/JPEG/JPG/SVG reais) | não importa (helper inexistente); o validador antigo aceita 11/12 entradas maliciosas | 75 passam |
| `static/js/test/security-logo-xss-runtime.js` (3) | `companyLogoSrc`, `companyLogoMarkup` e `applyBranding` lidos do código real | 3 falham | 3 passam |
| `scripts/browser/security_logo_xss.py` (Chromium, 5 idiomas, 8 cenários) | Login, topo e marca da plataforma, Empresas, Minha Empresa: malicioso não executa, legítimo aparece | maliciosos executam (4/4) | 40/40 |

Suítes completas: pytest 4.559 passaram; a única falha é `test_migration_phase2_formats[ods]`, que precisa do pacote
`odf`, ausente no ambiente local (falha igual na `main`). Testes JS: 653.

## 5. Auditoria independente

Agente separado, só leitura, sobre `1518afc7`/`91f7f37`. Conferiu:
- todos os caminhos de gravação e de exibição;
- a regex (`fullmatch` + `strip`; JS com `^…$` sem flag `m`; sem backtracking catastrófico);
- o escape;
- os logotipos legítimos (uploads e PDF);
- RBAC e isolamento, sem ciclos de importação;
- a paridade byte a byte com o SaaS.

Das mutações aplicadas, 13 foram detectadas. As 2 não detectadas (tirar o escape do `src` no `app.js` ou no
`tenant-init`) são equivalentes, porque a regex já impede os caracteres perigosos.

Achados e tratamento:

| Achado | Tratamento |
|---|---|
| **F1 (major)** — cadastro de Empresas: `login_logo_type`/`favicon_type` validados dentro de `try/except: pass`; o valor malicioso chegava ao `INSERT` | Validação estrita fora do `except` (cadastro) + testes do caminho de cadastro |
| **F2 (minor→major)** — valor legado fora da regra, reenviado pelas telas, bloquearia editar/suspender a empresa e salvar Minha Empresa/marca | Edição de Empresas saneia (campo protegido, restaurado pela rota); Minha Empresa e marca mantêm o valor gravado quando reenviado igual; testes |
| **F3 (minor)** — lista de riscos residuais incompleta | Lista abaixo atualizada |
| **F4 (info)** — testes não cobriam cadastro nem o legado | Cobertos (75 testes) |
| **F5 (info)** — CodeQL | Nenhuma alteração de configuração; conferir no PR que o alerta original fecha |

Reverificação (mesmo auditor, sobre `24b18e24`/`5ff8bb4`): **aprovado, sem bloqueio**. O caminho que mantém a
imagem gravada só devolve o valor já existente no banco, nunca o enviado. Nenhum outro caminho de gravação deixa
passar imagem fora da regra. Reverter as correções faz 7 testes falharem. As duas lacunas apontadas (chamada de
`save_platform_brand` sem `previous`; logotipo de login da marca aceitando JPEG) ganharam testes.

## 6. Riscos residuais (fora deste PR — propostos como correções separadas)

- **APIs autenticadas devolvem o valor gravado sem saneamento.** `GET /api/my-company`, `/api/companies`,
  `platform_brand` e `user.logo_type` do bootstrap. A proteção contra valores antigos fica na exibição do app (e
  na resolução pública de tenant). Um consumidor novo dessas APIs precisa aplicar a mesma regra.
- **Antes de integrar, contagem de dados (só leitura):** quantas linhas têm `logo_type`, `login_logo_type` ou
  `favicon_type` começando com `data:` e fora da regra, mais o `platform_brand`. Essas imagens passam a aparecer
  como o logotipo padrão até um novo upload. Não alteramos dados reais.
- **Validação do white-label no cadastro ainda engole outros erros** (slug, cores…) no `try/except` preexistente.
  Fora do escopo: as imagens já saíram dele.
- **Ficha EPI em HTML: demais campos sem escape (alta).** `render_ficha_epi_html_document` insere sem escape
  colaborador, função, setor, EPI, CA, unidade, empregador, declaração e observações. A ficha é servida na mesma
  origem (`text/html`, sem CSP) e guardada em snapshot. Quem cadastra colaboradores/EPIs consegue injetar HTML.
  Proposta: escapar todos os campos no renderizador. Impacto: o `html_sha256` dos snapshots novos muda; os antigos
  ficam como estão.
- **Foto do EPI e assinaturas (alta).** `epi_photo_data` é gravado sem validação (`modules/epis/service.py`) e
  exibido sem escape em `static/js/views/epis.js` (lista de EPIs). `signature_data` entra na ficha HTML com
  `startswith('data:image')`. Proposta: a mesma regra de data URL base64 e escape.
- **Textos sem escape ao lado do logotipo:** `company_name`/`company_cnpj` no selo do topo (`static/app.js`,
  `refs.companyBadge.innerHTML`), o nome da empresa nos cartões do Comercial (`${item.name}`) e outros textos já
  registrados na auditoria UBX. Proposta: escapar em uma revisão dedicada.
- **CSP em Report-Only.** Passar a aplicar o CSP reduziria o impacto de qualquer XSS remanescente. Exige revisão
  dos scripts inline.
- **Valores maliciosos já gravados** continuam no banco até um novo upload ou a remoção da imagem (regravar o formulário os mantém). Não são mais exibidos (exibição
  saneada) e não aparecem na resolução pública. Uma limpeza de dados exigiria autorização (dados reais), então não
  foi feita.
