# Auditoria independente — badges Flutter

Escopo: Corporate working tree após `c1faf3a3`; duas pontes tipadas de apresentação e sete views. SaaS será espelhado/testado pelo root. Nenhuma fonte de produto foi alterada pelo auditor.

## Preservação comprovada

`flutter-badges-static-results.json`: retirando somente o novo import e substituindo LocalizedEpiBadge/LocalizedEpiStockBadge pelos nomes anteriores, as sete views ficam byte a byte iguais à base. Portanto permanecem exatamente iguais as expressões que escolhem o status, condições de null, ações, rotas, chamadas de API, permissões e classificação. Os arquivos de EpiBadge/EpiStockBadge do design system, ApiClient e política de navegação também são byte a byte iguais.

LocalizedEpiBadge recebe EpiBadgeStatus e delega o mesmo valor a EpiBadge, acrescentando somente label de dez recursos existentes. LocalizedEpiStockBadge recebe EpiStockStatus e delega o mesmo valor a EpiStockBadge, acrescentando quatro rótulos existentes. Os tipos não são intercambiáveis; normal/nearMinimum/critical/disabled permanecem separados do estado do catálogo. `null` continua sem badge; não vira normal ou zero.

Ligação real encontrada em Employee detalhe/lista, EPI detalhe/lista, Estoque, Configuração de Estoque e Nova Entrega. Não foi acrescentado wrapper sem consumidor ou regra de negócio no core de apresentação.

## Runtime independente e captura

O quarto teste de `flutter-billing-badges-runtime-final.log` passou, após os três de billing. Exercita os mesmos widgets ao trocar pt_BR/en_US/es_ES/fr_FR/no_NO em temas claro e escuro: 14 estados × cinco idiomas × dois temas = 140 comparações. Em cada caso, status canônico é o mesmo da instância original e decorações/cores são iguais. Todos os dez rótulos de catálogo e quatro de estoque correspondem aos getters esperados, com dependência de locale e sem API. Zero exceções de widget.

`flutter-badges-original-pt-vs-localized-fr.png` mostra a mesma fixture com Inter e EpiTheme: coluna original com defaults PT do design system e coluna com wrapper FR, mantendo status e cor. É comparação sintética lado a lado do widget, não captura histórica de uma página real ou de Android/iOS. Os nomes de enum à esquerda são legenda do harness, não interface adicionada ao produto.

## Linguagem e limites

Os recursos preservam os significados de ativo/inativo, vencido/vencendo, pendente/aprovado/rejeitado/em análise, sem estoque/crítico e os quatro estados de estoque da Unidade. Sugestões pontuais de redação FR/NO estão separadas em `FLUTTER_LINGUISTIC_REVIEW_PARTIAL.json`; não mudam classificações.

A execução independente validou as pontes e aparência dos badges, sem instanciar todas as sete views completas. A prova de Employees real nos cinco idiomas sem nova GET/escrita foi informada pelo implementador e não é apresentada como execução própria. Labels mais longos em telas estreitas/escalas maiores ainda dependem dos testes de integração de cada view; o teste isolado não certifica layout global. Sem novo defeito de contrato confirmado, sem aprovação integral do produto.

## Atualização somente de fonte/redação

O root aplicou as sugestões FR `Expire bientôt` e NO `Ikke på lager`, conferidas nos ARBs regionais/aliases e getters gerados. A captura e os 140 casos de runtime acima registram o passo anterior de auditoria: o PNG FR mostra `Expirant`, portanto é histórico e não representa os pixels finais. Não houve novo SDK ou regeneração pelo auditor; não foi refeito o teste de renderização após essa mudança de palavras. Os dois tipos e a delegação de status permanecem inalterados.
