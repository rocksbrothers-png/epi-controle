# Auditoria independente — Flutter alertas e locale

Escopo congelado: Corporate `624d89153bfbddfd2853810b521376dd7f1811ed` e checkpoint SaaS `75185fb`. Execuções independentes realizadas no Corporate com o SDK disponibilizado. Edições locais posteriores de formulários, PO, meses e altura dos cards não fazem parte desta revisão. Nenhuma implementação ou branch foi alterada pelo auditor; harnesses, relatórios e capturas estão somente em audit.

## Veredito restrito

Nenhum defeito bloqueante novo confirmado no bloco de apresentação de alertas e cabeçalho de locale. Regras de estoque/validade, RBAC, escopo, cálculos, payload, Bearer, refresh e retry permanecem preservados no escopo analisado. Há um overflow mobile preexistente dos KPI cards, documentado abaixo; portanto não há afirmação de ausência de regressões visuais em todo o Dashboard nem aprovação integral do I18N-FULL-V1.

## Preservação estrutural

`flutter-source-contract-results.json` usa o parser AST Dart/analyzer:

- Classes `_BearerInterceptor`/`_RetryInterceptor` e todos os métodos ApiClient exceto init têm AST exatamente igual à base anterior ao bloco.
- As instruções de init têm AST igual removendo somente o if que adiciona LocaleHeaderInterceptor aos dois clientes Dio.
- Todas as classes Dashboard, exceto o tile que passa a apresentar os textos localizados, têm AST exatamente igual. O tile continua escolhendo cor/severidade pelos campos canônicos type/severity do servidor.
- DashboardCubit, AuthCubit, política de navegação, SessionContext, endpoint/modelo summary e EpiKpiCard não foram alterados pelo bloco. A identidade/permissões do dispositivo e os cálculos do servidor não foram reimplementados.

O callback consulta a preferência efetiva por dispositivo em cada requisição e apenas substitui Accept-Language, removendo duplicatas por diferença de maiúsculas. Mantém os códigos existentes pt-BR/en-US/es-ES/fr-FR/no-NO, sem renomear as configurações Flutter. Nenhum campo de locale, identidade ou tenant é acrescentado ao corpo. A mudança em main apenas disponibiliza a instância existente de LocaleProvider ao callback antes da inicialização dos clientes.

## Provas independentes executadas

`flutter-independent-final.log` / `flutter-independent-results.json`: três testes externos passaram, com:

- pt_BR, en_US, es_ES, fr_FR e no_NO carregados pelos delegates gerados.
- 30 combinações de plural (0, 1, 2, 1234, -1, 0,5 em cada idioma), datas e dias aninhados, tamanhos/sem tamanho, medida e saldo negativo formatados.
- Nomes originais contendo HTML, `{count}`, `{stock}`, Æ/Ø preservados como texto opaco; JSON de entrada inalterado.
- Cinco casos de metadados ausentes, desconhecidos, inválidos ou com tipo incompleto por idioma: título e descrição legados completos preservados, sem mistura de título novo com descrição antiga.
- Interceptor preserva corpo numérico/status/ator/empresa/unidade, query e Bearer sintético; altera somente o cabeçalho de idioma, sem duplicatas.
- DashboardScreen real, incluindo a árvore de widgets de produção, renderiza o mesmo alerta nos cinco idiomas. Troca de locale não refaz a consulta summary: uma GET total, com a mesma query. Não foi testado apenas um Text substituto do tile.

`flutter-independent-capture-final.log`: seis testes passaram na execução com o harness de captura e os três testes direcionados reais de ApiClient. A reexecução independente confirma 401 → refresh → retry com o mesmo locale e payload canônico, Bearer atualizado apenas no retry e ausência de Bearer no cliente de refresh. Também verifica callback de locale não suportado. Não houve rede externa, autenticação real ou banco.

A execução complementar final `flutter-independent-readable-capture-final.log` passou os três testes do harness com a fonte Inter e tema EpiTheme.light. Não foram iniciadas novas validações após o pedido de serialização do root.

## Capturas sintéticas e achado mobile preexistente

Arquivos:

- `flutter-alert-before-fr-FR-desktop.png` / `flutter-alert-after-fr-FR-desktop.png` — 1280×900.
- `flutter-alert-before-fr-FR-mobile.png` / `flutter-alert-after-fr-FR-mobile.png` — 390×844.

Método: WidgetTester, Inter e EpiTheme.light; corpo de DashboardScreen extraído do commit Corporate auditado, com apenas URIs de imports relativos normalizados no harness. Antes: payload sintético completo sem presentation, exibindo as strings legadas PT. Depois: mesmo payload com presentation, exibindo francês. São evidências da renderização/fallback do widget atual com dados locais; não são capturas históricas do aplicativo de produção ou de uma execução nativa completa. Ícones e serviços de plataforma do harness também não certificam a aparência nativa.

Em 390×844 há overflow preexistente de **3,9 px** nos KPI cards com Inter/tema real, observado e registrado 12 vezes durante os relayouts de captura. A origem é a Column de `flutter/packages/epi_design/lib/components/molecules/epi_kpi_card.dart:37` dentro da grade existente do Dashboard. O teste inicial com a fonte padrão Ahem acusava 26 px; esse valor não deve ser confundido com a medida obtida com fonte/tema reais. O JSON de captura conserva os detalhes das ocorrências. O overflow foi registrado explicitamente pelo harness, sem ser apresentado como ausência de erro visual. O componente e a grade pertencem ao baseline preservado por AST; a correção posterior proposta pelo root não foi auditada neste checkpoint.

## Recursos e limites

O manifesto do bloco mapeia 24 recursos operationalAlerts para ARB, com suas versões base/país e delegates gerados. As provas de runtime preservam os cinco locales configurados, o operando numérico do plural e a separação da quantidade formatada. CA continua CA brasileiro; não foi introduzido CE ou identificador regulatório estrangeiro no bloco analisado.

A inspeção e execução acima não certificam todas as mensagens dos catálogos, todos os módulos Flutter, documentos/portais/exportações, RBAC do backend ou comportamento em Android/iOS reais. A execução independente ocorreu no Corporate; testes/paridade SaaS informados pelo root complementam a revisão, sem serem apresentados como execução própria. Os artefatos de snapshot/hashes e resultados sustentam somente este escopo, sem autorização de merge/deploy e sem alegação de cobertura integral.
