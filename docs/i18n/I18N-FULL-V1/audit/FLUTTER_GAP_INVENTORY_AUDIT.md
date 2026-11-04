# Inventário independente de lacunas Flutter — leitura estática

Snapshot app/design: 2026-10-28T15:45:57.226120Z; API adjacente: 2026-10-28T15:46:38.639043Z. HEAD Corporate no relatório: `46fd5d677a10e5c4d1be0732f40c31a7c7393719` com mudanças locais. Cada arquivo possui SHA-256 em `flutter-gap-inventory-summary.json`; nenhuma fonte mudou entre a captura e a conferência de hashes deste relatório. SaaS não foi reauditado por este scanner; paridade deve ser provada separadamente.

## Escopo e método

AST sintática externa (analyzer do flutter_tools), sem resolução de tipos, SDK do workspace, pub get, format, gen-l10n, testes Flutter ou escrita no produto. Foram lidos 168 arquivos de app/lib e epi_design/lib e 51 arquivos epi_api/lib adjacentes, sem falha sintática. Delegates de localizações do app foram excluídos; o pacote epi_api inclui seu adaptador gerado de auth. A classificação combina AST e leitura manual de consumers. AdjacentStrings e interpolações são mantidos como expressões; códigos dentro de uma interpolação podem aparecer como ocorrência separada.

O corpus contém 4774 expressões literais: **não é uma contagem de dívida total**. O CSV separa 109 ocorrências de prosa com sink confirmado e 8 ocorrências com dupla função (valor canônico e texto exibido). Esses números contam ocorrências, não recursos faltantes únicos; incluem repetições/fragmentos internos e devem ser agrupados antes de implementar. Também há 73 candidatos dinâmicos e 207 ocorrências de produção de mensagens em Cubits: não equivalem a 73/207 falhas. Dos dinâmicos, 34 usam catálogo, dois são dados livres e três são componentes genéricos. As exclusões estruturais continuam candidatas à revisão, não prova de completude.

## Lacunas verificadas para próximos blocos

| Superfície | Fonte/linha | Consumer e implicação |
|---|---|---|
| Empresa Master | core/widgets/create_company_dialog.dart:48–52,136–289 | Textos de planos (prosa), labels, validações, convite e ações em PT. Conservar nomes de planos e CNPJ. |
| Sair | core/shell/app_shell.dart:156 | tooltip literal em IconButton. |
| Detalhe colaborador | features/employees/employee_detail_screen.dart:78 | _DetailSection exibe título PT. |
| Arquivar/desarquivar | features/employees/employees_screen.dart:60,135,182,188,293,295,324–331; features/epis/epis_screen.dart:74,132,194,200,330,332,358–365; features/units/units_screen.dart:47,53,110,165,171,288,290,316–323 | Tooltips, confirmações AdjacentStrings/interpoladas, vazios e retenção/subtítulos PT. Preservar nome, motivo livre, histórico e prazo; formatar apresentação sem alterar política. |
| Detalhe EPI | features/epis/epi_detail_screen.dart:78,86–87,94,101 | _DetailSection/_DetailRow renderizam títulos, Vencido e dias sem catálogo. Manter CA brasileiro e cálculos de dias. |
| Visibilidade de módulos | features/settings/module_visibility_screen.dart:45–63,147 | Segundo campo de records é label PT: Text(r.$2):229, Text(module.$2):275, Text(m.$2):324. Primeiro campo é código de RBAC/config, preservá-lo. Erro local:147→281 também PT. |
| Devoluções | features/returns/returns_screen.dart:128–130 | _conditionLabels → conditionLabel:142 → Text:198; codes good/damaged/lost e cores intactos. |
| Estoque | features/stock/stock_screen.dart:198,482,487,492,690,694–695 | Contagem EPIs, filtros e notas de fabricante PT; _manufacturerNote usado em:534. Preservar regras, status, CA e PEPS, traduzir descrição/plural. |
| Notificação estoque | core/bloc/stock_cubit.dart:231–232 | AppNotification local → NotificationService → notification_overlay.dart:88/97, ligado em app.dart:98; título/corpo PT. |
| Nova requisição | core/bloc/purchases_cubit.dart:132 | successMessage PT → features/purchases/new_purchase_screen.dart:60. Erro:137→69 cru. |
| Importação CNPJ | features/legal_entities/paste_import_dialog.dart:111→145 | Prefixo linha PT agregado em _summary; dados/erros por linha devem permanecer identificáveis. |
| Ficha/competência | epi_api/lib/models/ficha_period.dart:32–33 | periodLabel contém meses PT → features/records/records_screen.dart:197. Contagem pendente também PT/manual plural em records_screen:206. |
| Tipo de prestador | epi_api/lib/models/outsourced_company.dart:125–127 | companyKindLabel PT → outsourced_companies_screen.dart:343. Seletor já usa _companyKindLabel(l10n,k):787: corrigir detalhe sem mudar valores. |
| Responsabilidade de EPI | features/outsourced_companies/outsourced_companies_screen.dart:662–667,690,798 | Mesmo valor epi_responsibility é persistido e mostrado:344/797. Criar label de apresentação, nunca traduzir valores/defaults enviados em body:740. |
| Transporte da troca de senha | core/api/api_client.dart:258 | Fallback local PT → ApiException.message → change_password_screen.dart:75/189. Não confundir com fallback genérico do form já localizado. |

## Erros de fluxos aparentemente traduzidos

`flutter-producer-consumer-traces.json/.csv` documenta 16 rastros concretos. FeedbackCubit:49/63/72/81/90/103 emite e.toString → FeedbackScreen:122, embora título e ações usem catálogo. ReportsCubit:92/121 → ReportsScreen:79, LegalEntitiesCubit:172 → LegalEntitiesScreen:95, MyCompanyCubit:66/76/88/99/110 → MyCompanyScreen:44 e SettingsCubit:94/121/144 → SettingsScreen:62 têm detalhe cru. O CSV dinâmico cobre os demais sinks de dialogs, portal, biblioteca, fornecedor, validade e forms.

Um sink cru prova ausência de mapeamento local, **não prova que toda resposta backend venha em PT**. É necessário testar envelopes reais e códigos existentes, preservar detalhe/status/código e isolar mensagem de apresentação. O Accept-Language já propagado pode localizar parte das respostas; não substitui análise de cada endpoint/transport exception. Sem erro estruturado, documentar fallback em vez de prometer tradução arbitrária de dados.

## Controles contra falsos positivos

- ReportsCubit:118 contém sucesso PT, mas ReportsScreen:72 ignora o texto e usa reportsRequestSuccess. Não é gap de sucesso.
- AuthError empty/network/invalid/etc. são códigos; LoginScreen:65–70 localiza ou usa fallback. StockConfig negative/range e CompanyAttention range também têm consumers locais.
- EmployeeFormScreen tipos Terceirizado/Temporário/etc. são dados canônicos; _employmentTypeLabel:141 já os traduz visualmente.
- Rotas, actor/company/unit IDs, tokens, Bearer, filas/opcodes, filtros/status, nomes de planos, nomes de pessoas/empresas, razões livres, códigos QR, CA/CPF/CNPJ/NR-6, SKU e MP não devem ser traduzidos cegamente. Autônimos do seletor de idioma não são cópia indevida.
- PortalFicha.periodLabel é um campo remoto diferente do getter FichaPeriod.periodLabel. PortalHomeScreen:346/412 o exibe: requer rastrear locale do backend; não atribuir os meses locais de FichaPeriod a esse consumer.
- TenantDomain.type_label remoto → my_company_screen.dart:356 precisa teste backend. status/SSL locais já usam labels traduzidos.

## Defaults compartilhados e limites

Há 21 ocorrências PT latentes em epi_design: badges:16–25/44–47, SearchBar hint:10, DataTable emptyMessage:31, SignaturePad:127/143/151 e EpiErrorState:40/53. No app atual, os badges operacionais passam por wrappers locais e os dois SearchBars passam hint explícito. Não foram encontrados usos reais do SignaturePad/DataTable/EpiErrorState no app/lib; portanto esta lista é dívida potencial do componente, não prova de tela ativa quebrada.

Não foram auditados recursos nativos Android/iOS, textos de permissões de plugins/SO, todos os formatos externos/documentos/backend, ou o conteúdo completo dos catálogos. Literais estruturais e valores de modelo pendentes continuam no CSV; StateError PT de StockApi.lookupQr:204 tem exposição não resolvida (Error não é Exception). O scanner não alcança toda tradução por análise de fluxo/tipos nem valida renderização, acessibilidade ou troca de idioma. O pedido integral permanece aberto.

## Artefatos

- flutter-all-literals-classified.csv: todas as 4774 ocorrências, caminho/linha/expressão/tipo/triagem/motivo.
- flutter-confirmed-ui-gaps.csv: sinks de prosa confirmados e valores com dupla função.
- flutter-records-defaults-enums-review.csv: records, defaults, labels de enums e valores canônicos/locais.
- flutter-dynamic-ui-sinks.csv e flutter-cubit-message-producers.csv: sinks e produtores sem simular tradução inexistente.
- flutter-producer-consumer-traces.json/.csv: rastros manuais e contraexemplos.
- flutter-gap-inventory-summary.json: escopo, hashes, contagens descritivas, limitações.

Nenhuma fonte, branch, dado ou documentação do repositório foi alterado pelo auditor.
