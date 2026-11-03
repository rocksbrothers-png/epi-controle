# I18N-FULL-V1 — continuação (transferência Codex → Claude)

Data: 03/11/2026. Este documento registra o diagnóstico, a matriz de requisitos e
o que esta continuação alterou. Não é certificação de cobertura integral.

## 1. Ponto de partida (Fase A)

| | Corporate | SaaS |
|---|---|---|
| PR do Codex | rocksbrothers-png/epi-controle#1060 (draft, aberto) | rocksbrothers-png/epi-controle-app#434 (draft, aberto) |
| Branch | `codex/i18n-full-v1` | `codex/i18n-full-v1` |
| HEAD inicial | `d6d79b3f910f1b6cdbd04db6e0ee3243ea3e574a` | `736345ecf35b67804a5e92e043389d3a90ddbe2d` |
| Atraso em relação à `main` | 9 commits (CSP-REPORT-REDACTION, deps) | 7 commits (PYMUPDF, deps) |
| Conflito com a `main` | só `.gitleaksignore` (listas de exceções independentes) | nenhum |
| CI do HEAD inicial | 22 aprovados, 4 pulados previstos (Android/Web sem segredo) | idem |
| Veredito do próprio Codex | READY FOR HUMAN MERGE DECISION: NO | idem |

A continuação parte do HEAD do Codex (todos os commits preservados; nenhum
force-push, nenhuma branch excluída) na branch `claude/inspiring-cray-iphlu3`.
O Codex deixou explicitamente pendentes: mensagens/erros dinâmicos do backend,
superfícies JS remanescentes, documentos e a matriz integral.

Idiomas oficiais: `pt-BR` (fallback), `en-GB`, `es-ES`, `fr-FR`, `nb-NO`.
Motor: `static/i18n.js`, somente por chave (sem lookup reverso de texto). Texto em
português fora de `tr`/`trEpi`/`textFor`/`bindText`/`data-i18n` aparece em
português em qualquer idioma.

## 2. Inventário medido (Fase B)

Medição sobre o HEAD do Codex + `main`, com os scanners do próprio repositório
(`scripts/i18n/scan_html.py`, `scripts/i18n/scan_js.cjs`). São candidatos de
revisão, não dívida exata: incluem rótulos de log e chaves técnicas.

- HTML estático: 113 ocorrências restantes = exatamente as 113 exceções técnicas
  justificadas em `html-exceptions.json` (tamanhos, IDs, siglas). Concluído.
- JS dinâmico: ~1.240 literais de prosa sem binding (≈700 no `app.js`); o maior
  bloco é o fluxo de Feedback/EPI em teste (`runDetailAction`, ~120) e o leitor
  de QR (~77).
- Backend: ~846 mensagens de erro/validação em português únicas; ~142 têm
  template em `apiErrors` (≈17%). As demais chegam ao usuário em português.
- Formatação: datas globais (`formatDate`/`formatDateTime`) e KPIs/histórico do
  Comercial estavam fixos em `pt-BR`.
- Qualidade: mojibake no próprio pt-BR (mensagem de acesso do novo usuário e
  aviso de senha provisória: `provisÃ\u0083Â£o`, `transferÃ\u0083Âªncia`).

## 3. Matriz de requisitos

Legenda: ✅ concluído e validado · 🟡 implementado sem teste suficiente · 🟠 parcial ·
⛔ não implementado · ➖ fora do escopo original. Corporate e SaaS têm o mesmo estado
(arquivos compartilhados idênticos; diferenças legítimas em `index.html`,
`api-client`, `pagamento`, `devolution`, `cadastro`).

| Requisito | Corporate | SaaS | Pendência | Risco |
|---|---|---|---|---|
| Comercial (painéis, cards, ações, contrato, exportações, impressão) | ✅ nesta continuação | ✅ | Rótulos vindos do backend (`action_label`, `summary` do histórico, `type_label` de domínio) | P2 |
| Funções sobrepostas com a UBX (`formatCompanyCurrency`, `updateTopbarCompanyBadge`, `renderMyCompanyDomains`) | ✅ nesta continuação + gate | ✅ | — | — |
| Troca de idioma sem recarregar | ✅ motor + redesenho do Comercial (sem loaders) | ✅ | Outras telas dinâmicas só retraduzem no próximo render | P2 |
| Formatação BRL/números/datas | ✅ Comercial e helpers globais de data | ✅ | 3 horários `toLocaleTimeString('pt-BR')` em avisos ainda não traduzidos | P3 |
| Login (validação, troca de senha) | ✅ nesta continuação | ✅ | — | — |
| Encerramento de sessão (3 avisos one-shot) | ⛔ | ⛔ | Contrato F2 (`test_343_f2_teardown_logout.py`) fixa `terminateSession('<texto pt-BR>')`; traduzir exige decidir o contrato | P2 |
| Recuperação de senha | 🟠 (HTML estático) | 🟠 | Mensagens do backend sem template | P2 |
| Menus, navegação, dashboard, alertas operacionais | ✅ (Codex) | ✅ | — | — |
| Empresas, Minha Empresa | ✅ (Codex + UBX) / 🟠 módulo `my-company-view.js` | idem | 7 literais no módulo | P3 |
| Usuários (mensagens de perfil/ativação, senha provisória, mensagem de acesso) | ✅ nesta continuação | ✅ | — | — |
| Compras, Portal do Fornecedor, conectores, e-mails/PDF novos | ✅ (Codex, Chromium 5 idiomas) | ✅ | `purchases.js` ~33 literais | P2 |
| Estoque | 🟠 | 🟠 | ~45 literais (`app.js`, `estoque.js`) | P2 |
| Entregas e devoluções, leitor de QR | ✅ mensagens do QR/câmera/compartilhamento/período, OCR de fabricação, reimpressão e fluxo guiado (`entrega-epi.js`); 🟠 templates com contagem (`Leitura finalizada. N código(s)…`) e assunto do e-mail ao gestor | idem | Templates restantes; devoluções (`devolution.js`) | P2 |
| Colaboradores | 🟠 | 🟠 | poucos literais | P3 |
| Relatórios | 🟠 | 🟠 | literais em `reports-view.js` e `app.js` | P2 |
| Configurações, retenção, feature flags | 🟠 (retenção ✅) | 🟠 | ~40 literais | P2 |
| Feedback / EPI em teste | ⛔ (maior bloco) | ⛔ | ~130 literais | P1 |
| Mensagens de erro do backend | 🟠 ~17% | 🟠 | ~700 templates em `apiErrors` ou metadados `i18n` nas respostas | P1 |
| Flutter | 🟠 (Codex: 983 mensagens/locale; inventário de 117 lacunas) | 🟠 | ver `audit/FLUTTER_GAP_INVENTORY_AUDIT.md` | P2 |
| Contratos/fichas/documentos assinados históricos | ➖ não retraduzidos (regra do Codex mantida) | ➖ | — | — |

## 4. O que esta continuação alterou

1. `main` integrada às duas branches. Corporate: `.gitleaksignore` com a união
   exata das duas listas (212 + 3 entradas `commit:arquivo:regra:linha`), sem regra
   nova.
2. Comercial e funções sobrepostas com a UBX traduzidos (60 chaves × 5 idiomas):
   KPIs, cards, ações, alertas, vencimentos, histórico, situação do contrato com
   binding vivo, estados vazios, exportação Excel/CSV, janela de impressão (outro
   documento: sai traduzida e com `lang`), mensagens de resultado, dica de plano,
   prévias de logotipo e domínios de Minha Empresa.
   - BRL é formatado no idioma ativo, sem conversão (antes `toLocaleString('pt-BR')`).
   - Troca de idioma redesenha só os painéis do Comercial, a dica de plano, as
     prévias e a data do topo. Não chama loaders, não recria o formulário comercial
     nem o de marca (`renderPlatformBrand` regravaria campos e por isso não é usado).
   - `companyLogoMarkup`/`companyLogoSrc` não foram tocadas: pertencem ao PR UBX
     rocksbrothers-png/epi-controle#1079 / rocksbrothers-png/epi-controle-app#453.
     O `alt="Logotipo de …"` fica para depois da integração daquele PR.
   - Segurança: dados de domínio (`full_host`, `cname_target`, `txt_record`,
     `verification_token`, `type_label`, ids) e o código do evento de contrato
     passaram a ser escapados; antes entravam crus no `innerHTML`. Instruções DNS:
     texto do catálogo sem marcação; só os valores escapados recebem `<strong>`/`<code>`
     (substituição por função, imune a `$&`).
   - E-mail do contrato (assunto/corpo padrão) permanece em português: é conteúdo do
     documento contratual brasileiro, editável e enviado ao contratante.
3. Login, troca de senha, Usuários, retenção e mensagem de acesso do novo usuário
   (39 chaves × 5 idiomas). O pt-BR da mensagem de acesso e do aviso de senha
   provisória foi corrigido (mojibake e concordância). O aviso “…login manual agora”
   manteve a redação pt-BR exigida pelo contrato F2.
4. `formatDate`/`formatDateTime` globais (`view-helpers.js`) seguem o idioma ativo,
   com fallback pt-BR para motor ausente ou código inválido; nenhum dos 52 usos
   alimenta valor de formulário, comparação ou payload.
5. Nenhuma API, permissão, regra de negócio, SQL ou backend alterado. Guarda UBX
   inalterada: 727 declarações, 104 endpoints, 0 ciclos.

## 5. Testes acrescentados

- `tests/test_i18n_commercial_gate.py`: em 32 funções do Comercial e nas três
  sobrepostas com a UBX, todo texto em português visível precisa passar por
  `tr`/`textFor` (ou estar na allowlist com motivo). Procura as funções no `app.js`
  e em `static/js/modules/**`, então acompanha a extração UBX. Reprova o código
  anterior (60 achados em 22 funções) e passa no atual.
- `scripts/browser/i18n_commercial.py` (no workflow Chromium): SPA real com API
  interceptada, 3 cenários × 5 idiomas — Comercial (texto, BRL no idioma, situação
  do contrato, troca ao vivo sem requisição e sem perder o formulário, nomes com
  marcação inertes, `PUT /api/companies/<id>` intacto), login vazio (aviso
  traduzido, sem POST) e mensagem de acesso (sem mojibake, dados intactos). O
  `app.js` anterior reprova os 5 idiomas.
- `run-tests.js`: formatação de data no idioma ativo e fallback pt-BR.

## 6. Integração com a UBX

- Conflitos de I18N × PRs UBX #1079/#453 (inalterados por esta continuação):
  `static/index.html` (gerado) e os dígitos `DIGESTO_PARIDADE_F4/F5B`, nos dois
  produtos. `static/app.js` e `.gitleaksignore` não conflitam; com a `main` não há
  conflito (verificado com `git merge-tree`).
- Resolução recomendada, quando um dos dois entrar na `main`: rebasear/mesclar o
  outro, regenerar `static/index.html` com `python scripts/build_index.py build`
  e recalcular os dois dígitos nos dois repositórios (o contrato exige o mesmo
  valor nos dois lados), nunca escolhendo um lado inteiro.
- Ordem sugerida: #1079/#453 (fatia pequena) antes; depois esta I18N. A I18N
  absorve o conflito de arquivos gerados, e o `alt` do logotipo é traduzido no
  módulo `shared/ui/company-logo.js` já extraído.

## 7. Condições para liberar a extração UBX do Comercial

1. Esta I18N integrada à `main` nos dois repositórios, com CI verde.
2. `tests/test_i18n_commercial_gate.py` verde na `main` (a extração deve mantê-lo
   verde; a lista de funções acompanha os módulos).
3. `scripts/browser/i18n_commercial.py` verde nos 5 idiomas após a extração.
4. #1079/#453 integrados ou conciliados (índice e dígitos regenerados).

## 8. Auditoria independente (agente separado, só leitura)

Sobre `5c104a3c`/`71ad568`. **Nenhum P0/P1.** Conferidos: hunks do `app.js` sem mudança de
payload/API/declaração; escapes (inclusive a técnica de marcadores das instruções DNS); handler de troca
de idioma sem loaders nem escrita em formulário; 99 chaves novas com placeholders idênticos nos 5 idiomas;
52 usos de `formatDate`/`formatDateTime` só de exibição; permissões e escopos intactos; paridade byte a
byte e dígitos iguais; conflitos só com os arquivos gerados do PR UBX; Chromium 15/15.

| ID | Sev. | Achado | Tratamento |
|---|---|---|---|
| F1 | P2 | `handleForcedPasswordChange` ainda tinha 2 textos pt-BR | Corrigido (`login.passwordChange.tooShort`/`.updated`) e função incluída no gate |
| F2 | P2 | Gate isentava o literal inteiro com `data-i18n`, allowlist por texto e cobertura só do Comercial | Isenção restrita ao texto do elemento ligado; allowlist da impressão removida (já em `tr`); login/Usuários cobertos; teste de bypass. Limites remanescentes documentados no próprio teste |
| F3 | P3 | Rótulos de domínio não retraduziam ao vivo | `data-i18n` nos rótulos e no estado vazio |
| F4 | P3 | `company.id` sem escape em `commercialActions` (preexistente) | Escapado |
| F5 | P3 | Um único `try` no redesenho do Comercial | Passos independentes, com encadeamento opcional |
| F6 | P3 | Redação en-GB (`Responsible`, `grantedEmail`) e apóstrofos mistos no fr-FR | Corrigido. Nomes de perfil nas mensagens (“Administrador”/“Usuário” × `role.*`) espelham o pt-BR e ficam para revisão terminológica |
| F7 | P3 | Nome dos arquivos exportados em português | Mantido (cosmético) |

## 9. Lote 3 — Entregas, leitor de QR, OCR e reimpressão (continuação)

- 77 chaves em `app.js` (`delivery.qr.*`, `delivery.share.*`, `delivery.period.*`, `delivery.replacement.*`,
  `stock.ocr.*`, `stock.reprint.*`, `common.unknownError`) e 35 no fluxo guiado de `entrega-epi.js`
  (`delivery.guided.*`, atrás da flag `entrega_epi_htmx_enabled`).
- Correções do pt-BR: “ler código da imagem.” (frase truncada) → “Não foi possível ler o código da imagem.”;
  maiúsculas indevidas (“Etiqueta Não encontrada.”, “permissão de Câmera”, “Área de Câmera”).
- Mantidos de propósito: comparações com texto do backend (`includes('não encontrado')`,
  `'temporariamente indisponível'`), as palavras validadas da reimpressão (`Perdeu`/`Rasgou`, explicadas no
  texto traduzido), `PURCHASE_APPROVAL_REJECTION_REASONS` (valores canônicos de Compras) e o assunto do e-mail
  de assinatura ao gestor (conteúdo documental).
- Chromium: cenário `delivery_qr_messages` (modo USB e sessão sem QR válido, sem gravação) nos 5 idiomas.
