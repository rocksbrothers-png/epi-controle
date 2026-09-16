# #343 PR 3 — F5-C: rascunho de formulário

**Resultado: critério de parada acionado. Nada de persistência foi implementado.**

A frente perguntava, antes de qualquer implementação: *a aplicação realmente
precisa dessa responsabilidade?* A resposta medida é **NÃO**, e este PR entrega
a análise, o contrato em testes que trava a decisão, e o destino do módulo e da
flag.

**Nenhum arquivo de produção alterado.**

---

## 1) Inventário dos formulários (Etapa 1)

Extraído dos `static/views/*.html` servidos, não estimado: **27 formulários,
315 campos**.

| Formulário | View | Campos | Sensíveis | hidden/pwd/file |
|---|---|---:|---:|---:|
| `commercial-form` | comercial | 37 | 12 | 1 |
| `delivery-form` | entregas | 33 | 9 | 8 |
| `my-company-form` | configuracao | 29 | 0 | 6 |
| `stock-form` | estoque | 23 | 1 | 1 |
| `epi-form` | epis | 22 | 0 | 4 |
| `legal-entity-form` | cnpjs | 16 | 3 | 2 |
| `employee-form` | colaboradores | 16 | 3 | 1 |
| `user-form` | usuarios | 14 | 1 | 2 |
| `outsourced-employee-form` | terceirizados | 12 | 1 | 1 |
| *(+ 18 formulários menores)* | | | | |

Tipos de dado presentes na superfície: CPF, CNPJ, e-mail, telefone/WhatsApp,
endereço, CEP, nome, matrícula (`employee_id_code`), data de admissão, cargo,
setor, dados de entrega de EPI, assinatura (`delivery-signature-data`),
QR/códigos de leitura, senhas, tokens de recuperação e IDs internos.

### Achado estrutural: **142 dos 315 campos não têm `id`**

O phase41 indexa por `id` — `if (!field || !field.id) return false`. Quase
metade da superfície é invisível para ele.

Isso não é detalhe: o `#employee-form`, que o comentário do próprio `app.js`
cita como o caso mais sensível ("CPF, nome, e-mail e WhatsApp de um
colaborador"), tem `cpf`, `name`, `email` e `whatsapp` **sem `id`** — só com
`name`. O phase41 não os alcança.

**A cobertura do phase41 é um acidente de markup, não um desenho.** Um `id`
acrescentado amanhã a um campo de CPF muda a superfície persistida sem que
ninguém perceba. `PR3 A-1` mede e trava esses números.

### Matriz de dados

| Tela/formulário | Precisa de rascunho? | Dados presentes | Persistência permitida? | Justificativa |
|---|---|---|---|---|
| `commercial-form` | **sim** | contratante/prestador: nome, CNPJ, endereço, e-mail, telefone; corpo de e-mail | **já existe, server-side** | `/api/commercial-contract/save`, `status: draft` |
| Cotações/pedidos de compra | **sim** | fornecedor, itens, valores | **já existe, server-side** | `QUOTE_STATUSES = ('draft','sent',…)` no banco |
| Fluxo de teste de EPI | **sim** | avaliação técnica | **já existe, server-side** | `rascunho → em_analise_tecnica → …` |
| `employee-form` | não demonstrado | CPF, nome, e-mail, WhatsApp, matrícula, admissão | **não** | dado pessoal de terceiro; política ativa manda apagar |
| `delivery-form` | não | assinatura, QR, IDs de estoque | **não** | contrato F5-B: reentrada chega ao estado inicial |
| Filtros de lista (todas as telas) | **sim** | busca livre, `company_id`, `unit_id` | **já existe** | snapshots de navegação SPA, escopados |
| `login-form`, `password-change-form` | não | senha, chave de recuperação | **nunca** | credencial |
| Demais 20 formulários | não demonstrado | cadastro e configuração | **não** | sem requisito; dado relido do servidor |

---

## 2) Owners existentes (Etapa 2)

A busca por owner **antes** de criar infraestrutura encontrou **três**
mecanismos já implementados:

1. **Rascunho server-side de domínio** — contrato comercial
   (`/api/commercial-contract/save`), cotações e pedidos de compra
   (`status draft|sent|answered|…` no banco), fluxo de teste de EPI. É onde o
   requisito é real, e a resposta do projeto foi o servidor. `PR3 A-6`.
2. **Snapshots de navegação SPA** — guardam **filtros digitados**
   (`employeesFilters`, `episFilters`, busca livre, `company_id`/`unit_id`),
   carimbados por `snapshotScopeId()`, em `sessionStorage`, invalidados pelo
   encerramento **e** pela troca de principal. `PR3 A-4`.
3. **Rascunhos em memória** — `state.stockAlertEditor.draft` (chaveado por
   unidade, justamente para não vazar entre unidades), `state.migracao`,
   `state.signatureDraft`.

Não há lacuna que justifique um quarto sistema.

---

## 3) A política ativa é a oposta

`resetAppFormDrafts()` **apaga** rascunho de formulário, e o faz por lista de
**exclusão** — "limpa-se TUDO, menos a única exceção que o contrato exige"
(`#login-screen`). Alcança deliberadamente controles **fora** de `<form>`,
porque `form.reset()` não os alcança e é ali que mora rascunho sensível
(`#compras-supplier-name`, `-cnpj`, `-email`, `-notes`). `PR3 A-3` mede os dois
casos.

Some-se o contrato F5-B, já testado: **reentrar num módulo chega ao estado
inicial**. E a conclusão do PR 2D: estado digitado não deve ganhar segunda
cópia implícita.

Implementar restauração de rascunho no cliente seria remar contra três
decisões já tomadas, testadas e comentadas.

---

## 4) Por que o desenho do phase41 não serve como referência (Etapa 3)

| Exigência da frente | O que o phase41 faz |
|---|---|
| Nada persistido por padrão | Varre **todo** `input[id], select[id], textarea[id]` do documento |
| Allowlist explícita | Lista de **exclusão** por regex em id/name |
| Namespace com tenant/usuário/view/schema | Chave única e global: `epi:ux:phase41:context:v2` |

A lista de exclusão é
`(password|token|cpf|cnpj|signature|assinatura|document|recovery|qr|code|key|secret|access|link)`.
**Não conhece** `email`, `phone`, `telefone`, `whatsapp`, `endereco`, `address`,
`cep`, `matricula`. `PR3 A-2` afirma cada uma dessas ausências e mede o efeito
sobre a superfície real: campos como `commercial-contractor-email`,
`commercial-contractor-phone`, `commercial-provider-address` e
`commercial-email-body` passariam.

É a demonstração exata do que a Etapa 3 adverte: *CPF, e-mail, telefone,
matrícula e endereço não são seguros simplesmente porque não são password.*

---

## 5) Identidade e trust boundary (Etapa 5)

| Camada | De onde vem | Confiável? |
|---|---|---|
| `state.user` (frontend) | `safeStorageRead(STORAGE_KEYS.session)` → `localStorage['epi-session-v4']` | **não** — o cliente controla |
| `actor_user_id` (requisição) | body/query, cruzado com o token quando presente | parcial |
| **Autoridade real** | **JWT Bearer**, HMAC-SHA256 sobre `JWT_SECRET`, claim `sub`, com `exp` | **sim**, no servidor |

E a exigência do JWT ainda está em rollout: `JWT_ENFORCEMENT` tem modos
`off`/`shadow`/`enforce`, com **`shadow` como padrão em produção** — mede sem
bloquear.

**Consequência direta para esta frente:** o frontend não tem identidade própria
com que namespacear nada. Uma chave `draft:<tenant>:<user>:…` montada no cliente
seria carimbada com um valor que o próprio cliente controla — isso **repete a
afirmação do cliente**, não prova isolamento. `PR3 A-5`.

Para fazer isolamento de verdade seria preciso derivar o namespace de identidade
autenticada — o que significa servidor. E no servidor o mecanismo já existe.

---

## 6) Comparação A/B/C (Etapa 10) — `PR3 A-7`

| | **A — remover sem substituição** | B — draft para formulários selecionados | C — mecanismo geral seguro |
|---|---|---|---|
| Benefício | elimina 455 linhas inertes e uma chave global | rascunho onde fosse autorizado | rascunho em toda parte |
| Telas realmente beneficiadas | — | **0** | **0** |
| Superfície de dados | nenhuma | a allowlist que fosse definida | 315 campos, 27 formulários |
| Risco | nenhum | médio — dado pessoal em disco do cliente | alto |
| Complexidade | trivial | allowlist + ciclo de vida + isolamento | + TTL + versão de schema + namespace por tenant/usuário |
| Manutenção | nenhuma | allowlist envelhece a cada campo novo | idem, multiplicado |

**A contagem de telas beneficiadas é zero nas duas alternativas** porque
nenhum requisito foi encontrado: não há menção a rascunho de formulário em
`docs/`, em `spec/`, nem no produto — e onde havia requisito real ele já está
resolvido no servidor. A própria "F5-C" não tem especificação: a única
ocorrência no repositório é a referência futura que eu mesmo escrevi no doc do
PR 2D.

**Escolhida: A.** É a solução mínima que atende ao requisito comprovado — que é
nenhum.

---

## 7) Ciclo de vida, armazenamento, minimização (Etapas 6, 7, 8)

Não se aplicam: sem mecanismo, não há criação, atualização, restauração,
expiração nem escolha de meio a definir. Registrado aqui para que a ausência
seja deliberada e não omissão.

Se a decisão for revista no futuro, o caminho indicado é **estender o owner
server-side existente** (`status: draft` por domínio), não criar armazenamento
no cliente — é o desenho que já resolve identidade, isolamento por tenant e
ciclo de vida, e que o projeto já adota onde o requisito é real.

---

## 8) Testes (Etapa 9)

As suítes de isolamento, ciclo de vida e segurança **não foram escritas porque
não há mecanismo para exercitar**. Escrevê-las seria simular um sujeito que não
existe.

No lugar delas, sete gates travam a **decisão**, e falham se alguém reintroduzir
persistência sem refazer a análise:

| Gate | Trava |
|---|---|
| `PR3 A-1` | superfície real (27 formulários, 315 campos, ≥130 sem `id`) e a cobertura acidental do phase41 |
| `PR3 A-2` | a lista de exclusão não conhece e-mail/telefone/endereço/CEP/matrícula, e o efeito medido |
| `PR3 A-3` | a política ativa apaga rascunho, inclusive fora de `<form>` |
| `PR3 A-4` | o owner de estado digitado é o snapshot, escopado e descartado na troca de principal |
| `PR3 A-5` | o frontend não tem identidade própria; a autoridade é o JWT no servidor |
| `PR3 A-6` | onde o requisito é real, o rascunho já existe server-side |
| `PR3 A-7` | comparação A/B/C, destino do módulo e da flag, e a colisão de guarda intocada |

Regressão: os contratos do PR 1 e do PR 2 seguem verdes (396 gates).

Uma correção durante a execução: a primeira versão do `A-4` afirmava que
`rotateSnapshotScope()` **gera** um escopo novo. O gate reprovou. O mecanismo é
outro — ele **descarta o escopo herdado** e volta ao do documento atual, que é o
que fecha o cenário documentado no app (F5 sem encerramento, troca de
principal). O gate foi reescrito para medir o mecanismo real.

---

## 9) Destinos (Etapas 11, 12, 13)

**`ux-phase41.js` → REMOVER — RESPONSABILIDADE DESNECESSÁRIA.** Vai para a fila
do PR 4.

O que ele fazia além do rascunho — estado de botão no submit, indicador global
de carregamento (por um terceiro monkey patch, agora sobre `globalThis.api`),
foco no primeiro campo, fechamento de overlays (já do `app.js`, PR 2C/2D) — são
afordâncias que nunca rodaram e não carregam regra de negócio. Nenhuma sustenta
a preservação do arquivo.

**`ux_phase41_enabled` → REMOVER NO PR 4.** Fica órfã junto com o módulo. Não há
mudança de governança de flag a justificar: ela nunca chegou a ser lida em
produção, porque a colisão de guarda barra antes.

**Bootstrap (Etapa 12): não corrigido, deliberadamente.** Com o módulo indo
embora, a colisão deixa de ser problema. `PR3 A-7` afirma que ela continua lá,
para que uma "correção" silenciosa quebre o gate.

### Fila do PR 4, atualizada

| Item | Origem |
|---|---|
| `ux-phase43.js` | PR 2A |
| `ux-phase44.js` (incl. bridge de fetch e `createDropdown`) | PR 2B / 2C |
| `multitab-navigation.js` | PR 2D |
| ouvintes órfãos de `epi:action-*` no `ux-analytics.js` | PR 2B |
| **`ux-phase41.js`** | **PR 3** |
| **flag `ux_phase41_enabled`** | **PR 3** |
| flags `ux_phase43_enabled`, `ux_phase44_enabled`, `ux_multitab_navigation_enabled` | ficam órfãs com os módulos |
| chaves legadas em `localStorage`: `epi:ux:phase41:context:v2`, `epi:ux:phase41:scroll:v2`, `epi:ux:phase43:state:v1`, `epi.ux.phase44.filters.*` | PR 0 registrou que permanecem no disco |

A última linha merece atenção no PR 4: remover o módulo **não apaga o que ele já
gravou**. A limpeza precisa sobreviver à remoção do código que a executava.

---

## 10) O que este PR não fez (Etapa 14)

Não removeu `ux-phase43.js`, `ux-phase44.js`, `multitab-navigation.js` nem os
ouvintes órfãos — todos do PR 4. Não corrigiu bootstrap, não mexeu em flags, não
fez limpeza estética nem refactor não relacionado.

**Impacto comportamental esperado: zero.** Nenhum arquivo servido ao navegador
foi alterado.
