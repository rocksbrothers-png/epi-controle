# Auditoria independente de DI e fronteiras do passe C

Escopo: trabalho Corporate durante o passe C, seguido da revisão congelada Corporate `3693b04f7a7f6a50d60466f73fb3a72e883408df` / SaaS `a96107c`. Não constitui aprovação integral de I18N-FULL-V1. Nenhuma fonte de produto, branch ou banco foi alterado pelo auditor.

## Evidências verificáveis

- `matching-di-probe.log`: 1.200 conjuntos aleatórios em cinco idiomas, 6.000 comparações e 245.845 invocações do formatador. Sem callback, saída exatamente igual à implementação anterior. Com callback, candidatos, elegibilidade, bloqueios, contradições, sugestões, quantidade de erros e conteúdo das linhas/assinaturas permaneceram iguais. Um callback vazio também não mudou decisões. O mecanismo mantém motivos canônicos; somente a apresentação usa o DI.
- `purchase-live-decisions-results.json`: Chromium com HTML e módulos reais de Compras. Decisões `8 / ignore / 9` e confirmação preservadas nos cinco idiomas. Os dados assinados originais permaneceram intactos e o handler de gravação conservou IDs, assinatura, campos originais e preços numéricos. Transporte e parser foram portas locais; não é teste de HMAC ou autorização do backend.
- `pass-c-boundaries-probe.log`: cinco idiomas, comparados à base `3e6fe8c5`. Mapas de papéis/permissões, defaults, chaves de armazenamento, valores canônicos de devolução, vínculo/filtro de terceirizados e payload comercial iguais. Gate não Master não gerou PUT no harness. Isto não substitui testes de RBAC no servidor.
- Defeito confirmado e corrigido pelo implementador: getter traduzido no campo persistido `saveCommercialSettings.payload.corporate.plan.label`. A prova posterior exige `Corporate` literal e igualdade integral do payload com a base. Defaults já haviam sido restaurados. Os 187 getters inventariados em `pass-c-localized-getters.json` não apresentaram outro consumidor de gravação; os cinco internos a funções pertenciam a renderização de retenção/ranking.

## Checkpoint congelado posterior

`frozen-payment-contract-results.json` compara funções extraídas dos commits: `postJson`, `basePayload`, `selectOption`, `getJson`, `showResult` exatamente iguais antes/depois nos dois projetos; Corporate também `newIntentKey` e `getAuthToken`. Corporate mantém Bearer e nonce estável por intenção; SaaS mantém capability pública `checkout_token`. Nenhum arquivo de backend de pagamento/auth/permissões mudou no intervalo analisado. Não houve transação de pagamento real.

Engine, Biblioteca, render_worker, uno_convert e constantes/permissões JS têm paridade byte a byte entre os dois HEADs. Diferenças autorizadas de checkout foram preservadas.

`frozen-core-probe.log` reexecuta em Chromium a engine e os módulos extraídos do commit, cobrindo escape de valores, SVG/elementos filhos, observação de DOM, dados não marcados, motivos canônicos e bindings reutilizados após vazio/erro. Sem erros de página. `frozen-attributes-probe-results.json` cobre cinco idiomas, atributos de estado, alteração do texto de um filho sem perder binding do label, ownership de atributo, clearBinding, mensagem real da Biblioteca, payload imutável, chave de protótipo inválida e texto livre não correspondente. Zero imagens injetadas e zero erros de página.

Revisão do diff do preview: `name` original preservado; `name_i18n_key` adicionado apenas a nomes gerados Documento/Imagem. Nomes de abas Office continuam originais. O consumidor escapa título, nomes e chaves em atributos; bindText escapa parâmetros. Limites de conteúdo, extensão, sandbox, páginas/pixels e regras de autorização não foram alterados. Esta auditoria não refez a conversão Office real; as evidências de renderização fornecidas pelo implementador não são apresentadas como execução independente.

## Limites e pendências

Não é certificação funcional de todo o produto ou dos cinco idiomas. Flutter, todos os documentos/relatórios e todos os erros backend permanecem fora destas provas. O checkout ainda apresenta JSON/dados de provedor e erros por wrapper próprio; a UI do Brick FR/NB usa inglês suportado pelo provedor. Cobertura residual deve continuar explícita. A paridade dos módulos analisados não prova ausência de divergências em todas as superfícies dos repositórios.
