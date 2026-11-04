# Auditoria independente — formulários, meses e layout Flutter

Revisão do Corporate working tree posterior a `624d8915`, separada de `FLUTTER_ALERT_LOCALE_AUDIT.md`. A etapa inicial foi somente estática, respeitando a serialização. Após liberação explícita do root, uma única execução Flutter independente confirmou a correção de mensagens e do layout nas condições abaixo. O relatório histórico e suas capturas continuam documentando o checkpoint anterior; não foram sobrescritos.

## Resultado restrito da inspeção

Não foi encontrada mudança nas condições de validação, requests, códigos canônicos, autenticação ou transições de estado analisadas. A lacuna inicial de retradução dos erros de validação foi corrigida e confirmada independentemente em PT→FR→EN. O Dashboard corrigido passou em 390×844, escalas 1 e 1,3, sem overflow e sem nova consulta. Não foi confirmado novo defeito concreto neste recorte; isso não equivale a cobertura integral do produto.

`flutter-forms-layout-static-results.json` registra hashes, comparação direta de seis arquivos críticos com a base e os 16 recursos novos de cada locale: 12 de senha e quatro de fornecedor/PO. ApiClient, AuthCubit, DashboardCubit, ReportsCubit, SessionContext e política de navegação permanecem byte a byte iguais à base no momento da inspeção. Nenhuma fonte foi alterada pelo auditor.

## Preservação de contratos

### Senha temporária

- `_submit` continua limpando a mensagem, chamando Form.validate antes da API e enviando somente currentPassword/newPassword dos mesmos controllers. Mounted, loading/saving, completePasswordChange e logout mantêm os caminhos existentes.
- Validação de senha atual vazia, mínimo de seis caracteres, diferença da senha temporária e confirmação igual continuam exatamente com as mesmas condições. Apenas os textos retornados foram substituídos pelos getters de localização.
- ObscureText, alternância de visibilidade, controllers, dispose, formKey, envio pelo teclado e bloqueio dos botões enquanto salva foram preservados.
- ApiException continua mostrando sua mensagem específica. O fallback genérico passa a ser localizado; não altera status/código/credenciais.

### Confirmação de PO

Os DropdownMenuItem continuam com values `confirmed`, `delivery_update`, `rejected`; estado inicial e fallback permanecem `confirmed`. O Navigator.pop continua devolvendo status, delivery_forecast, carrier, tracking_code e comment dos mesmos campos, com o mesmo trim. Os rótulos e o hint de data ISO são apresentação. AAAA-MM-JJ em francês descreve ano/mês/dia, sem mudar o formato enviado.

### Relatórios

A lista de meses mantém inteiros de 1 a 12 (`index + 1`), apenas rotulados por DateFormat.MMMM. O ano 2000 é constante para gerar nomes, sem entrar no request. `_selectedYear`/`_selectedMonth` permanecem os mesmos estados e são enviados a requestReport sem conversão em texto. A seleção de anos e cálculo de currentYear não mudaram. `_periodLabel` usa DateFormat.MMM para meses válidos e mantém o fallback numérico do mês inválido, preservando o ano original.

### Dashboard e design system

A grade passa de proporção fixa a mainAxisExtent calculado pela escala de texto. Os quatro KPIs continuam vindo dos getters do estado; NumberFormat muda somente a representação. `criticalStock == null` continua sendo travessão, sem inventar zero. Nenhum recálculo, fetch ou escopo foi acrescentado.

EpiKpiCard passa a envolver o valor completo em FittedBox(scaleDown), preservando a string, estilo, delta e callbacks. EpiButton usa Flexible no rótulo e altura mínima em lugar de altura fixa; variantes, padding, cores, callback, fullWidth, spinner e disabled/loading permanecem existentes. A inspeção não substitui testes do design system em seus diferentes pais/constraints e escalas.

## Lacuna inicial — corrigida neste bloco

`change_password_screen.dart` continua guardando `_error` como String; o fallback é traduzido dentro do catch e depois exibido diretamente por Text(_error). Uma reconstrução por mudança de locale não refaz essa tradução armazenada.

Além disso, validators traduzem no momento de Form.validate, mas os TextFormField usam autovalidate desabilitado por padrão. A implementação do SDK em `widgets/form.dart` armazena o retorno em `_errorText` e didChangeDependencies não revalida no modo disabled. Portanto os textos de validação já exibidos podem continuar no idioma anterior após a mudança de locale, mesmo que os labels mudem. Essa foi a constatação da primeira revisão estática, antes da correção. A fonte corrigida e a prova independente posterior estão descritas abaixo. Não se recomenda limpar controllers, reenviar senha ou alterar autenticação para resolver apresentação.

Também não se declara resolvida a internacionalização das mensagens específicas ApiException: elas foram preservadas e dependem do trabalho mais amplo de erros backend/Flutter.

## Evidências do implementador e próximos limites

O root informou 20 casos de senha/gate/recursos e 30 cenários de Dashboard (cinco idiomas × três tamanhos × duas escalas), com KPIs até 12.345.678, sem overflow/refetch/mutação. Esses resultados foram considerados contexto, não execução independente do auditor. A execução independente autorizada posteriormente cobriu a transição de erros e dois cenários mobile; os demais casos continuam sendo evidências do root. Não há aprovação integral do produto nem reavaliação retroativa da auditoria histórica de 624d8915/75185fb.

## Revisão estática da correção posterior de senha

O root tratou a lacuna identificada. A revisão da fonte posterior confirma que didChangeDependencies agenda somente Form.validate após uma mudança real de locale e após submit prévio (`_hasValidated`). O callback verifica mounted e não chama `_submit`, API ou completePasswordChange. Os mesmos controllers/validators permanecem; portanto a atualização é de mensagens já solicitadas pelo usuário, sem criar requisições ou alterar credenciais.

O erro genérico agora é representado por `_genericError` e traduzido em build no locale corrente; ApiException.message continua como texto opaco e específico. A fonte já não conserva o fallback genérico traduzido em `_error`. A lacuna estática inicial está tratada nesta versão. A confirmação independente de runtime foi concluída depois da liberação, conforme a seção seguinte.

## Execução independente após liberação

Uma execução Flutter, somente com o harness externo `flutter_forms_layout_independent_test.dart`, terminou com **dois testes passando**. Log: `flutter-forms-layout-runtime.log`; JSON: `flutter-forms-layout-runtime-results.json`.

1. Formulário real: após submeter valores inválidos, PT→FR→EN remove as mensagens anteriores e apresenta as novas mensagens de mínimo/comparação. Os três controllers conservam os valores sintéticos originais. O ApiClient não foi inicializado nesta etapa: os dados inválidos não alcançam requests. Nenhuma exceção de widget. A atualização do fallback genérico por `_genericError` foi revisada na fonte; não foi simulada falha de API para esse fallback nesta execução.
2. DashboardScreen real, locale fr_FR, Inter/EpiTheme/MaterialIcons, viewport 390×844, escalas 1 e 1,3. KPI grande é `12 345 678` e os demais `1 234`; todos permanecem presentes. Nenhum overflow foi suprimido: `tester.takeException()` deve ser nulo depois do layout e do scroll até o alerta. Escopo/JSON do servidor intactos, query original preservada, uma única GET `/api/dashboard/summary` para toda a troca de escala.

Capturas pós-correção: `flutter-postfix-dashboard-fr-FR-mobile-scale1_0.png` e `flutter-postfix-dashboard-fr-FR-mobile-scale1_3.png`. São widgets reais com transporte e dados sintéticos. O scroll foi posicionado para mostrar o valor grande, podendo deixar a parte superior dos primeiros cards fora da viewport. Os dados, escala e posição de scroll diferem das capturas históricas com KPIs pequenos; não constituem comparação pixel a pixel e não substituem uma execução Android/iOS. O achado histórico de 3,9 px em 624d8915 continua válido naquele contexto; este novo snapshot confirma a correção nas duas configurações testadas.

Os dez casos PO/relatórios e 39 testes do design system informados pelo root permanecem evidências do implementador; não foram reexecutados pelo auditor nesta única execução autorizada. Na revisão independente desses fluxos, requests, códigos e tipos foram examinados estaticamente. O relatório não aprova merge/deploy ou I18N-FULL-V1 integralmente.
