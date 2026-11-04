# Auditoria independente de alertas

Snapshot Corporate `3f32341d` / SaaS `9ff2e44`; escopo restrito ao bloco de apresentação dos alertas. Sem alterações de produto ou bancos.

## Defeito confirmado de apresentação

`alert-presentation-browser-results.json`, gerado em Chromium com os arquivos extraídos do commit, comprova duas manifestações da mesma incompatibilidade entre referência numérica e seleção de plural:

- O alerta de validade do fabricante próxima apresenta `{daysLabel}` literal nos cinco idiomas. Exemplo PT: `... vence em 31/12/2026 (em {daysLabel}). ...`.
- O binding de quantidade física permanece em inglês após troca EN→FR somente pela engine: `2 physical items.` em vez de `2 pièces physiques.`. O rerender completo do Dashboard pode mascarar essa segunda manifestação, mas não torna o binding válido.

Causa verificável: alert-presentation.js cria `daysLabel` como mensagem plural com `refs.count = numberRef(days)`. resolveMessageVars formata count como string e `_message` só seleciona plural quando `Number.isFinite(vars.count)` é verdadeiro. O mesmo ref transforma o count de physicalDescription. O count canônico usado para plural deve permanecer numérico enquanto a apresentação do número pode ser localizada separadamente. Não foi implementada correção pelo auditor.

## Preservação comprovada

`alert-backend-rules-results.json`: removendo da AST somente o novo helper `_presentation`, os campos `presentation` e atribuições locais `title_key`, o backend é exatamente igual ao checkpoint anterior `3693b04f`. Classificação de estoque/validade, filtros, contagens, datas, escopo, identificadores e strings legadas permanecem estruturalmente intactos. As cinco versões de operationalAlerts têm 28 folhas, mesmas chaves e placeholders.

`alert-navigation-results.json`: nos dois projetos, `_alertAction`, `_bindAlertActions`, `_openViewFiltered`, `isCriticalAlert` e `renderCriticalStockBanner` são exatamente iguais ao checkpoint anterior. Módulos backend/helper/dashboard têm paridade byte a byte nos dois HEADs.

O probe Chromium também comprova, nos cinco idiomas:

- Busca pelo título traduzido e pelo tamanho identifica o alerta correspondente.
- Datas e números tipados são localizados sem modificar os dados de entrada.
- EPI, empresa, unidade e tamanhos contendo HTML/aspas permanecem texto; zero elementos img/svg/b injetados e nenhum script executado.
- Frontend com helper ausente, payload sem metadados e chave futura desconhecida mantêm a mensagem legada completa, incluindo tamanhos, com escape seguro.
- Clique encaminha os mesmos identificadores company_id=31, unit_id=51, epi_id=71 e nome original ao helper existente. A ausência de stock:view remove o botão específico de validade desconhecida. Nenhuma escrita/API real executada.
- Zero erros de página e input JSON intacto.

## Limites

Prova estrutural não substitui toda a integração com o banco; a autorização do backend não foi retestada por HTTP neste probe. O teste de clique usa porta local para capturar destino/escopo. Não foram refeitos mobile, tecla Enter ou leitura do sistema inteiro nesta auditoria. Este relatório não aprova I18N-FULL-V1 integralmente nem confirma correção posterior às evidências do snapshot.

## Reteste da correção no working tree Corporate

A correção posterior aos commits congelados foi copiada para `audit/alert-retest-current`, com hashes dos três módulos no resultado. `alert-presentation-retest-results.json` comprova em Chromium: cinco idiomas sem placeholders pendentes; 30 casos de plural físico e 30 de mensagem de dias aninhada (0, 1, 2, 1234, -1, 0,5 em cada idioma), todos com operando canônico intacto e número formatado; EN→FR sem rerender retraduz quantidade física, botão e aria-label com o nome original do EPI. As verificações anteriores de escape, busca, fallback, gate e escopo continuam passando. Zero achados e zero erros de página neste reteste restrito.

O patch privado `_pluralCount` separa o operando numérico do texto formatado; seu Symbol não é serializado em metadados DOM/JSON ou payload. As duas manifestações confirmadas acima estão corrigidas neste snapshot ainda não commitado. Isto não altera o veredito restrito de escopo nem aprova o produto integral.
