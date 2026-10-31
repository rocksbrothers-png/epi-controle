# SECURITY-OUTPUT-XSS-V2 — nomes de colaborador, unidade e EPI renderizados como HTML

Base: Corporate `c39b6092` / SaaS `192213d` (já com SECURITY-OUTPUT-XSS-V1 e FIX-USERS-ACTIVE-V1).
Continua a V1 (`docs/SECURITY_OUTPUT_XSS_V1.md`, §5), que corrigiu nome de empresa/CNPJ, ficha HTML, foto do EPI e
Comercial, e deixou como risco residual o texto de colaborador, unidade e EPI nas demais telas.

## 1. Gravidade

**Alta.** XSS armazenado. Os textos abaixo chegavam a `innerHTML` sem escape, em telas abertas por perfis com mais
privilégio que quem os grava:
- nome, matrícula, setor, função, empresa de origem e contato do colaborador;
- nome e cidade da unidade;
- nome, fabricante e CA do EPI;
- os mesmos textos copiados em entregas, estoque, demandas e requisições de compra, arquivamento e relatórios;
- títulos e descrições de alerta, montados no servidor com o nome do EPI, da empresa e da unidade.

O Gestor de EPI e o Administrador Local gravam colaborador e EPI. O Administrador Geral, o Master e os compradores
abrem as listas, o dashboard e as compras.

## 2. Reprodução (Chromium, `main` `c39b6092`)

`scripts/browser/security_output_xss_v2.py`: varredura de dado contaminado.
- **Dados:** todo texto de cadastro de colaborador, unidade e EPI chega como `<img src=x onerror=…>`, no bootstrap e
  nas rotas de estoque, compras, arquivamento, relatórios e requisição (10 rotas).
- **Execução:** o app real abre as 12 telas e todas as abas, e chama os renderizadores pontuais (formulário de
  usuário, configuração, gaveta de entrega, detalhe de requisição, relatório).

| | Execuções do payload | Elementos injetados | Contêineres afetados |
|---|---|---|---|
| `main` | **148** | 105 | 37 |
| Com a correção | **0** | 0 | 0 |

Na `main`, o cenário legítimo também falha: o título da gaveta de entrega mostrava a entidade (`&amp;`) no nome do
EPI, por escape duplicado.

Os 35 contêineres da `main` são:
- **Colaboradores:** lista, Gestão de Colaboradores, arquivados, terceirizados.
- **Unidades:** lista e arquivadas.
- **EPIs:** arquivados.
- **Estoque:** EPIs e estoque baixo.
- **Entregas:** histórico e filtros.
- **Dashboard:** últimas entregas e alertas.
- **Relatórios:** colaborador, unidade, setor, fichas.
- **Compras:** demandas, requisições, detalhe, unidade da PO.
- **Fichas:** colaborador, filtro, auditoria.
- **Usuários:** vínculo de colaborador e busca.
- **Configuração:** unidade das regras.
- **Selects de unidade:** colaborador, EPI, terceirizado, estoque.

## 3. Correção

O escape é aplicado na saída, no ponto em que o texto entra no HTML. Nenhum dado gravado mudou.

- **Helpers:** `escapeHtml` global no `app.js`; nos módulos, o helper local de cada arquivo (`escapeText`, `esc`,
  `escapeAttribute`). `devolution.js` ganhou o seu.
- **Texto legítimo:**
  - texto sem `& < > " '` sai idêntico;
  - campo ausente continua saindo como antes (`${v}` dentro do escape);
  - com esses caracteres, o visual é o mesmo e o HTML usa a entidade.
- **Itens corrigidos por arquivo:**

  | Arquivo | O que foi escapado |
  |---|---|
  | `app.js` | relatório de entregas; JoinVenture; selects de colaborador da entrega, do vínculo de usuário, da configuração e da auditoria de ficha; busca de vínculo; opções de unidade do vínculo; etiquetas de estoque (popup de impressão); regras de configuração; demandas e requisições de compra (lista, detalhe, PO); unidades da requisição; fornecedor autorizado; setores do relatório; linha de tempo de retenção |
  | `dashboard.js` | alertas (título, descrição, botão); últimas entregas |
  | `devolution.js` | tabela de entregas (empresa, matrícula, colaborador, EPI, quantidade, medida, atributos `data-dev-*`, condição); opções de entrega de origem |
  | `employees-view.js` | linhas (matrícula, nome, setor, função, unidade, empresa de origem, contato, `aria-label`); opções de unidade; popup do link de acesso |
  | `units-view.js` | nome e cidade na lista; opções |
  | `outsourced-*-view.js` | opções de unidade |
  | `archival-view.js`, `unit-archival-view.js` | nome, matrícula, unidade, razão social, CNPJ, CA, motivo, responsável |
  | `epi-registration.js` | opções de unidade |
  | `reports-view.js` | select de colaborador; fichas por colaborador; tabela de arquivo |
  | `estoque.js` | tabela de EPIs; estoque baixo |
  | `fichas.js` | select de colaborador; auditoria de ficha |

- **Fallback do drawer de entrega:** o fallback devolvia o texto cru e agora também escapa. O título, que já é
  escapado pelo drawer, não é mais escapado duas vezes (antes aparecia `&amp;` no nome do EPI).
- **Sem mudança em:** rotas, RBAC, isolamento multiempresa, regras de negócio, dados gravados e textos de interface
  (5 idiomas).

### Rodada da auditoria independente

A auditoria somente leitura aprovou com correções. Apontou dois bloqueios, reproduzidos no Chromium nos dois
projetos.

- **B1. Modal "↩ Devolver":** o EPI e o colaborador eram lidos de volta dos atributos `data-dev-*` (o navegador
  decodifica as entidades) e iam crus ao `innerHTML`. Agora são escapados.
- **B2. Tamanhos (luva, tamanho, uniforme):** são texto livre, e a solicitação do portal do colaborador também os
  aceita. Agora são escapados em:
  - histórico de entregas;
  - estoque (saldo por tamanho, estoque baixo, solicitações);
  - movimentações;
  - painel de saldo da entrega;
  - demandas de compra;
  - aprovações.

  Os helpers compartilhados (`formatItemSizeDisplay` e `formatSizeBalancesDisplay`) não mudaram: outros chamadores
  já escapam a saída, e mudá-los geraria escape duplicado.
- **Itens a corrigir:**
  - proteção e unidade de medida do EPI no estoque (os rótulos devolvem o valor desconhecido inalterado);
  - requisitante (`created_by_name`) nas requisições;
  - `User-Agent` na auditoria de ficha.
- **Guarda:** inclui os campos acima, contexto de atributo e interpolação depois de outra; o limite está documentado.
- **Varredura:**
  - passa a exigir as 10 rotas contaminadas e a reprovar se um renderizador não existir ou lançar erro;
  - clica em "↩ Devolver";
  - contamina tamanhos, proteção, medida e requisitante;
  - no cenário legítimo, confere os três textos e a ausência de `&amp;`, `&lt;`, `&gt;`, `&quot;` e `&#39;`.

  Sobre o código anterior a esta rodada, a nova varredura acusa 19 execuções, e 0 depois.

## 4. Testes

| Teste | `main` | Com a correção |
|---|---|---|
| `scripts/browser/security_output_xss_v2.py` (Chromium, 5 idiomas): malicioso (nada executa, nada injetado, as 10 rotas contaminadas exigidas, renderizadores conferidos, modal Devolver aberto) e legítimo (`Ana & "Bia" Ltda`, `Base D'Água`, `Luva <nitrílica>` aparecem como texto, sem entidade visível) | 148 execuções; legítimo falha | 10/10 |
| `tests/test_security_output_xss_v2_guard.py`: guarda que falha se um template de `static/` interpolar (após tag, após outra interpolação ou em atributo) ou concatenar texto de cadastro cru | 65 + 5 pontos crus | 0 |
| Caracterizações UBX (colaboradores, terceirizados, arquivamento, unidades) | — | 665 testes JS |

Sobre as caracterizações:
- Os próprios dados de teste já tinham HTML em nomes: `Bruno "B" Lima`, `Base <A>`, `Ana <b>QA</b>`,
  `SPE "x" & <i>y</i>`.
- A referência congelada reproduzia a saída vulnerável. Em `Bruno "B" Lima`, o nome fechava o atributo `aria-label`.
- A referência e os valores esperados passam a usar o mesmo escape, com comentário.

## 5. Pendências registradas (sem alteração de dados)

Herdadas das demandas anteriores e mantidas como registro, conforme a autorização:

- **Usuários Master sem registro no histórico empresarial:** ativar ou desativar um Master não gera entrada, porque a
  trilha é por empresa (FIX-USERS-ACTIVE-V1).
- **Contas possivelmente reativadas antes da correção:** contas reativadas indevidamente antes da
  FIX-USERS-ACTIVE-V1 continuam ativas. Identificá-las exige cruzar logs. Nenhum dado foi alterado.
- **Criação de usuário com `active=0` ignorado:** comportamento anterior (`int(payload.get('active', 1) or 1)`);
  o formulário não oferece essa opção.
- **Falha preexistente do teste ODS:** `tests/test_migration_phase2_formats.py::…[ods]` falha localmente com
  `ModuleNotFoundError: No module named 'odf'`.
  - Falha na `main` dos dois projetos (`c39b6092` e `192213d`), antes destes PRs. Não foi introduzida por eles.
  - No CI, que instala a dependência, passa.

## 6. Riscos residuais

- **Valores maliciosos já gravados** continuam no banco. Não executam mais nos pontos corrigidos; a limpeza exigiria
  autorização.
- **CSP do app em Report-Only:** a camada que bloquearia o que escapar desta varredura. Proposta: SECURITY-CSP-V1.
- **Telas fora do escopo:** avaliações de EPI, biblioteca de segurança, migração, portal do colaborador e portal do
  fornecedor não fazem parte da varredura, por conterem outros tipos de dado.
  - Elas não interpolam os campos cobertos pela guarda.
  - Uma varredura própria pode ser feita em demanda separada.
