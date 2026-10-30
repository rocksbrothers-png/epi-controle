# I18N-FULL-V1 — implementação em andamento

Este é um checkpoint de implementação, não uma certificação de cobertura integral.

## Etapas

- A: inventário inicial registrado em `inventory-A.json` e `inventory-A.csv`.
- B: bindings estáticos e grande parte dos fluxos dinâmicos de Compras implementados; revisão de mensagens, formatação, portal do fornecedor e documentos ainda em andamento.
- C: 906 ocorrências do inventário HTML inicial receberam bindings, além do placeholder de e-mail do checkout. As 113 ocorrências técnicas restantes estão enumeradas e justificadas em `html-exceptions.json`. Rótulos adicionais de navegação e módulos usam o catálogo central. O checkout anteriormente limitado a PT/EN já usa os cinco idiomas, com testes de desktop/mobile, formatação BRL e preservação da seleção e contrato de checkout de cada produto. O restante do JavaScript dinâmico continua em revisão.
- D: CA brasileiro e CPF identificados explicitamente nos rótulos web e Flutter. Revisão linguística/glossário completo e demais textos Flutter ainda pendentes.
- E: testes direcionados e revisão independente parciais. Navegação integral em cinco idiomas, matriz funcional final, paridade e CI finais ainda pendentes.

Os valores em reais permanecem BRL. A tradução não converte moedas, CA/CE ou documentos pessoais. Valores canônicos de motivos, permissões, IDs, linhas assinadas e decisões da associação são preservados.

A geração de novos PDFs declara a codificação WinAnsi e escapa o texto uma única vez. Documentos históricos assinados, snapshots, contratos já emitidos e arquivos originais da Biblioteca permanecem no idioma original e não são retraduzidos, regravados nem reassinados.

## Veredito deste checkpoint

- TECHNICAL VERDICT: não emitido; implementação incompleta.
- GOVERNANCE VERDICT: validação final pendente.
- READY FOR HUMAN MERGE DECISION: NO.

## Evidência do checkout

As capturas `evidence/checkout-before-fr.png`, `evidence/checkout-after-fr-FR.png` e `evidence/checkout-after-mobile-fr-FR.png` mostram a correção com dados sintéticos. O relatório `evidence/checkout-results.json` registra os cinco idiomas, preço BRL, seleção e intenção preservadas, zero erros JS e nenhuma requisição de escrita. API e SDK de pagamento foram substituídos por portas locais: não comprova transação financeira real.

O componente de cartão do Mercado Pago é externo e oferece somente os locales do próprio provedor; a interface ao redor usa os cinco idiomas do produto. O adaptador usa português, espanhol ou inglês no componente, sem renomear os locales configurados do EPI Controle. Conteúdo/recibos originais do provedor não são retraduzidos.

## Biblioteca e revisão linguística

A Biblioteca recebeu bindings de filtros, categorias, estados, datas, metadados e mensagens de erro específicas. Os testes usam documentos sintéticos e verificam os cinco idiomas, formulários preenchidos, escape de conteúdo e celular. Os metadados adicionais de pré-visualização identificam somente nomes gerados pelo sistema; nomes de planilhas e documentos originais permanecem intactos.

Foram aplicadas 120 recomendações linguísticas da revisão independente, registradas em `linguistic-corrections.json`. A avaliação prévia é apresentada como avaliação preliminar e a autoridade do Administrador Geral permanece distinta do Master.

## Alertas e aliases Flutter

Os alertas operacionais passaram a receber metadados de apresentação aditivos; títulos e descrições legados, condições, severidades e identificadores permanecem. O módulo de apresentação usa datas/números/plurais e preserva empresa, unidade, EPI e tamanhos. Testes locais em Chromium cobrem os cinco idiomas, busca por tamanho localizado, Enter, leitura, escape de valores e celular. Não houve regularização ou outra escrita.

Os cinco ARBs base do Flutter foram sincronizados com seus respectivos catálogos regionais. O gerador oficial 3.47.7 foi executado. Um teste dos delegates gerados compara todas as 781 mensagens entre pt/pt_BR, en/en_US, es/es_ES, fr/fr_FR e no/no_NO, incluindo parâmetros. Isso elimina o fallback acidental causado pelos aliases parciais; não certifica tradução de toda a interface Flutter, cujos hardcodes ainda precisam de revisão.

CI do checkpoint 3693b04f: Portal Docs aprovado no run 40434076866. Backend e Flutter reprovaram; foram encontrados e corrigidos import F401, manifesto ARB desatualizado e verificações estáticas que não reconheciam getters/bindings de tradução. Nova execução será vinculada ao próximo HEAD. Sem aprovação integral ou autorização de merge.

## Portal do fornecedor e erros de cotação (em validação)

A página pública `/fornecedor/<token>` usa o catálogo central nos cinco idiomas e um seletor sem persistência na conta do painel. O transporte foi extraído para `purchases/integrations/supplier-portal-api.js`; token, endpoints e payloads de resposta/confirmação permanecem. O teste Chromium cobre cotação editável, cotação respondida, pedido e link inválido em cada idioma, troca com campos/arquivo preenchidos, mensagens específicas, sucesso e celular. Toda a API é interceptada com dados sintéticos.

Os 42 templates de erro de `quotes_service.py` e `supplier_portal_service.py` receberam recursos nos cinco idiomas (54 ocorrências rastreadas no manifesto), sem mudar as mensagens no backend. Procurement passou a localizar seus erros mantendo status, código, payload e metadados para retraduzir feedback/toast. Outros templates de Compras e backend ainda estão pendentes.

A auditoria independente detectou contagem formatada como string quebrando plurais aninhados e a retradução de peças físicas. O core agora preserva o operando numérico separado do texto de apresentação; o teste verifica 1.234 peças, 0/1/2 e dias aninhados em EN→FR→EN. A prova dos alertas foi ampliada para lote próximo do vencimento e troca sem rerenderizar o dashboard.

Os workflows Backend CI, Flutter CI, Contract Tests e Backend Isolation Guard aprovaram ambos os HEADs de alertas/aliases (Corporate `3f32341d`, SaaS `9ff2e44`). Resultados e SHAs estão em `CI-RESULTS.json`; os novos ajustes posteriores ainda precisam de CI no próximo HEAD.

## Novos e-mails e PDFs de Compras

RFQ, PO e e-mail do Portal do Fornecedor usam recursos centrais e locale da requisição. O serviço de apresentação tem instâncias imutáveis por requisição e Babel/CLDR, sem locale global do processo. A variante Flutter en_US conserva a formatação dos EUA usando o catálogo de inglês existente; no_NO usa o catálogo Bokmål existente. Identificadores, CA brasileiro, quantidades originais, destinatários e cálculos não mudam; BRL não é convertido. O arredondamento de apresentação .2f dos floats foi preservado, inclusive 2.675. Nomes/observações são interpolados uma única vez.

A seleção de idioma ocorre depois das verificações existentes de autorização/escopo. Novos links do fornecedor carregam apenas lang na query de apresentação; token, hash, validade, entidade e isolamento permanecem. Nenhuma preferência ou idioma de fornecedor foi criado no banco. Na ausência de um idioma explícito, os builders mantêm português como idioma padrão. Falhas de catálogo/chave impedem gerar um documento no idioma errado ou com chave crua.

O layout dos novos anexos quebra linhas e pagina os itens, acomodando traduções maiores. Os nomes localizados dos anexos mantêm o identificador original. Documentos e e-mails históricos não são regravados. `evidence/documents/` contém PDFs/textos sintéticos dos cinco idiomas e capturas antes/depois; nenhum transporte de e-mail foi invocado. A auditoria independente extraiu dez PDFs com 125 itens em três páginas e validou 210 apresentações concorrentes, além da preservação estrutural de SQL, auditoria, destinatários, tokens e guardas. Relatórios/documentos dos outros módulos seguem pendentes.

## Integração concorrente

A main avançou com FIX-NAV-REFRESH-V1 durante a implementação. A simulação registrada em `UBX-INTEGRATION.json` não foi aplicada ao worktree e não criou commit de merge. Foram encontrados conflitos em app.js, nos cinco catálogos, no index gerado e nos dois digests de paridade. Os SHAs observados da main e os caminhos sobrepostos estão no relatório. A integração precisa preservar tanto os novos contratos de navegação quanto os bindings desta tarefa; as branches do Claude permanecem intactas. A implementação integral e a integração final continuam pendentes.

## Flutter — alertas operacionais e locale das requisições

O dashboard móvel usa os metadados aditivos dos alertas com recursos ARB centrais equivalentes aos da web. Os 24 recursos novos preservam nomes e tamanhos originais, formatam datas/números e mantêm o operando numérico dos plurais separado do texto de exibição. Metadados incompletos ou desconhecidos conservam a mensagem legada inteira. Não foram acrescentadas condições de classificação, ações, permissões ou mutações. Os delegates gerados agora são comparados em todas as 805 mensagens dos cinco pares base/região.

O transporte Dio recebe o locale efetivo do LocaleProvider a cada requisição, incluindo refresh/retry, usando os códigos existentes pt-BR/en-US/es-ES/fr-FR/no-NO no Accept-Language. Não são acrescentados campos ao corpo ou à query. Bearer, ator, empresa/unidade e persistência de preferências permanecem no contrato anterior. Os testes locais passaram 33 casos em cada projeto, incluindo o refresh real com adapters sintéticos, preservação de payload e troca de idioma. A análise estática dos arquivos novos passou sem apontamentos; ARB/guarda UBX e paridade de 276 arquivos passaram. Isso não certifica os hardcodes restantes do Flutter.

O Backend CI aprovou o checkpoint anterior de documentos nos dois projetos (Corporate 51794c00, SaaS 0576de5), incluindo a suíte completa, PostgreSQL, JS e provas de navegador. Os links vinculados a SHA estão em CI-RESULTS.json. O próximo checkpoint Flutter exige sua própria execução de CI.

A auditoria independente parcial exercitou o DashboardScreen real nos cinco idiomas, com uma única consulta ao summary durante as trocas. Os adapters externos confirmaram que locale altera apenas o cabeçalho de apresentação, preservando Bearer, query e JSON. A matriz incluiu plurais, datas/dias, tamanhos, nomes opacos e fallback completo. Evidências parciais em audit/flutter-independent-results.json; relatório consolidado do bloco em preparação.

## Flutter — formulário de senha, PO, meses e layout responsivo

Foram acrescentadas 16 mensagens ARB por idioma (12 de senha e quatro de confirmação do fornecedor), com aliases e delegates gerados oficialmente. Os cinco catálogos regionais agora têm 821 mensagens, verificadas pelo teste exaustivo dos delegates. O formulário usa os mesmos controllers, mínimo de seis caracteres, comparação e gate de senha temporária. A troca de idioma retraduz erros já exibidos somente após submit prévio, sem reenviar senha nem apagar campos. O erro genérico guarda estado de apresentação, e mensagens específicas ApiException continuam preservadas, pendentes da revisão global de erros.

A confirmação de PO localiza os rótulos e o hint ISO, mantendo confirmed/delivery_update/rejected e o payload original. Os relatórios usam Intl para meses longos/abreviados, mantendo mês 1–12 e ano inteiros; observações não são traduzidas. Dez testes de widgets/transportes sintéticos comprovaram esses contratos nos cinco idiomas.

A grade do dashboard acomoda a escala de texto e formata os quatro KPIs sem recalcular dados; null continua como travessão. O valor completo do card pode reduzir sua escala para caber. Botões deixam o rótulo longo quebrar linha e preservam altura mínima, ações, loading e estilos existentes. Trinta cenários do dashboard (cinco idiomas × três tamanhos × duas escalas) e os 39 testes do design system passaram no Corporate. A revisão independente confirmou PT→FR→EN com erros e campos preenchidos, e dashboard francês real em 390×844 com escalas 1/1,3 e contagens grandes, sem overflow, mutação ou refetch. Capturas pós-fix têm dados/scroll diferentes das históricas, como explica o relatório; não são comparação pixel a pixel nem teste Android/iOS.

Flutter CI aprovou o checkpoint anterior 624d8915/75185fb nos dois projetos. Backend CI teve uma única falha em cada projeto: regex de teste que exigia a assinatura antiga de ApiClient.init, sem o callback opcional de idioma. Corporate passou os demais 4.447 casos; SaaS, 4.388. A regex foi ajustada para exigir baseUrl obrigatório e aceitar somente o callback opcional, preservando as verificações de atribuição de baseUrl e isolamento de hosts. Os 25 testes desse contrato passaram localmente em ambos. O novo HEAD precisa de CI próprio; a internacionalização integral continua incompleta e READY permanece NO.

Validação final local deste bloco: 32 testes Flutter direcionados no corporate, 25 testes de release/baseUrl no corporate; os testes novos são os mesmos nos dois produtos. Os dez casos adicionais do Corporate pertencem ao gate de senha temporária preexistente naquele repositório. Resultados em evidence/flutter-forms-results.json.

## Flutter — assinatura e histórico financeiro

As duas telas usam o catálogo central (41 novas mensagens; 862 por locale regional), com formatação Intl de datas/valores e preservação de BRL, IDs, período, status canônicos e URLs originais. O arredondamento .2f dos doubles ocorre antes de adicionar separadores, preservando 2.675→2.67. Datas mantêm o calendário original, sem conversão de fuso; entradas inválidas permanecem opacas. Mensagens de dialog/SnackBar dependem do locale no contexto interno. O valor de faturas pode quebrar linha para caber no celular.

Os 28 testes direcionados passaram em cada projeto, além da prova adicional de recibo com porta de plataforma simulada. Trocar idioma conserva o filtro e o dialog aberto, sem nova consulta nem POST; cancelar continua exigindo confirmação. Fixtures de leitura negada/ausência de assinatura não apresentam ação de cancelamento. Isso não substitui teste de RBAC real: API, modelos, interceptors e verificações de backend permanecem intactos. Os 41 recursos têm consumidores rastreados em flutter-billing-message-sources.json.

A guarda estática do KPI foi adaptada à apresentação Intl, exigindo a condição null→travessão e a formatação somente para valor definido; a proibição de null→zero permanece. O widget real foi ampliado para distinguir respostas null e zero após refresh explícito. A suíte equivalente ao Backend CI (tests/) passou no Corporate: 4.471 aprovados, 49 ignorados. No SaaS, 34 testes direcionados de contrato de consumo/paridade passaram. A invocação exploratória sem selecionar tests/ também descobriu a suíte PostgreSQL separada sem DATABASE_URL; ela não é apresentada como aprovação e não alterou bancos compartilhados. Os jobs PostgreSQL aplicáveis continuam sendo verificados no CI isolado.

Capturas antes/depois e limites constam de evidence/billing-capture-results.json e audit/BILLING_REVIEW_STATUS.md. A auditoria independente deste bloco foi interrompida por limite de uso e permanece pendente; não foi emitida aprovação integral.

## Flutter — ligação de rótulos existentes

Foram conectadas 25 ocorrências literais de sete views a recursos já existentes: ações de arquivar/desarquivar, motivo, nome completo, empresa, tipo, notas, perfil, fechar/tentar novamente e canais de fornecedor. Nenhuma mensagem foi acrescentada aos catálogos; permanecem 862 por locale. O manifesto enumera cada ocorrência em flutter-existing-message-bindings.json. Outros títulos, textos dinâmicos, validações e dados de enum ainda estão pendentes; isto não certifica as sete telas integralmente.

Os itens de popup usam um contexto local para acompanhar o idioma enquanto o menu está aberto; cancelamentos e rótulos dos dialogs também leem o locale do próprio dialog. O teste de EmployeesScreen real passou nos dois projetos: cinco idiomas no popup conservam value=archive e nenhuma nova consulta; FR→EN no dialog conserva o motivo digitado, sem escrita ao cancelar. A comparação AST do implementador confirma condições if, valores nomeados e ações exatamente iguais nas sete views. Não equivale a auditoria independente ou prova de RBAC real. Os 36 testes direcionados de paridade/consumo/migração passaram no Corporate.

Backend CI e Flutter CI aprovaram ambos os HEADs financeiros 0f83da08/7480dbc; os links constam de CI-RESULTS.json. O próximo HEAD de bindings exige suas próprias execuções. A auditoria independente global, as lacunas remanescentes e a integração concorrente com main continuam pendentes. READY permanece NO.


## Flutter — indicadores de catálogo e estoque por unidade

Sete views usam wrappers de apresentação para os dez status do catálogo e os quatro status de estoque por unidade. Os wrappers usam 14 getters ARB existentes (13 recursos únicos), preservam os enums separados e delegam cores/estilos aos componentes originais. Não classificam estoque nem convertem ausência de classificação em normal. Labels personalizados e os componentes do design system permanecem intactos; o catálogo continua com 862 mensagens por locale regional.

Os 21 testes direcionados passaram em cada projeto: 14 status × cinco idiomas × temas claro/escuro, troca com os mesmos widgets montados, comparação de cores/estilos com os badges originais, labels personalizados opacos, EmployeesScreen real e testes preexistentes de separação catálogo/unidade. As 34 guardas de consumo e paridade também passaram em ambos; a guarda de source aceita o wrapper e exige a delegação do enum intacto. Analyzer dos dois arquivos novos sem apontamentos. O manifesto cobre 287 arquivos. Isso não certifica todas as telas nem substitui RBAC real.

Backend CI e Flutter CI dos checkpoints c1faf3a3/272697a9 aprovaram os dois produtos. O bloco de badges necessita de CI no próprio HEAD. Auditoria independente parcial em retomada; READY FOR HUMAN MERGE DECISION continua NO.


## Flutter — avaliações, diálogos e revisão independente retomada

A tela de avaliações passou a localizar título, filtros, ausência de dados, erro de carregamento, validação e os 21 status atuais/legados. Dezessete novos recursos elevam os catálogos regionais a 879 mensagens. Os valores null/open/in_review/resolved dos filtros, classificação de cores, condições das ações, decisões administrativas, API, Cubit e modelo permanecem. Status desconhecidos e textos originais de colaborador/unidade/EPI/descrição continuam opacos. O erro específico da API permanece preservado; a tradução global de erros ainda está em andamento.

Os dois diálogos consultam o idioma pelo próprio contexto e possuem seu controller até o unmount da rota. Isso corrige o descarte antes do fim da animação, detectado pelo teste de troca de idioma/cancelamento. Trim, guards null/vazio e chamadas administrativas permanecem. A data usa DateTime.parse igual à implementação anterior antes do Intl, inclusive a normalização UTC de timestamps com offset; não houve alteração temporal de dados.

Corporate passou 26 testes direcionados (20 cenários reais nos cinco idiomas, mapeamento de status/data e cinco pares dos delegates); SaaS passou os mesmos 26 e o teste de 14 indicadores × cinco idiomas × dois temas. Carregamento foi mantido por porta sintética pendente, seguido de sucesso/vazio/erro. Filtros preservam os códigos e somente uma seleção explícita consulta novamente; trocar idioma mantém filtro, input e quantidade de leituras. Nenhuma escrita foi feita nesses testes de avaliações. Não certificam RBAC real nem os demais módulos. Analyzer da tela registra somente três infos de underscores preexistentes, sem erros/warnings nos arquivos analisados.

Nove sugestões linguísticas independentes foram aplicadas: concordância/pagamentos FR de assinatura, validade próxima FR, item sem estoque NO e ação corretiva NO. Encerrado/Fechado e Reprovado/Rejeitado têm rótulos distintos. Auditoria independente de billing/badges foi retomada: quatro testes externos passaram; fonte, resultados e limites foram incorporados. Feedback recebeu revisão independente estática e linguística; seu runtime foi validado pelo implementador. A captura dos badges é anterior às últimas correções de redação e está marcada como histórica. As capturas de avaliações usam os widgets reais anterior c1faf3a3 e atual, fixture idêntico, fontes reais e viewport FR 390×844, sem erros ou escrita.

O manifesto de paridade passou com 295 arquivos sincronizados. A lista de allowlist perdeu três entradas migradas; o gate continua bloqueando novas strings. A matriz funcional integral, os demais hardcodes/backend/documentos e a integração concorrente continuam pendentes. READY FOR HUMAN MERGE DECISION: NO.


## CI — guarda de classificação da entrega

Flutter CI aprovou 5baea4bc/3010613f nos dois produtos. Backend Test & Coverage reprovou somente a verificação estática que exigia o nome antigo EpiStockBadge imediatamente após if(status != null). As outras 4.459 verificações passaram no Corporate e 4.400 no SaaS. A guarda null permanece intacta. O teste foi adaptado para exigir LocalizedEpiStockBadge, o tipo EpiStockStatus e a delegação sem transformar status; as outras referências ao componente foram tornadas explícitas. Os 47 testes direcionados de entrega/consumo passaram em cada projeto. O novo HEAD exige Backend CI próprio. A etapa seguinte de formulários ainda está em desenvolvimento e não integra esta correção de teste.


## Flutter — formulários de usuários/unidades, retenção e QR

Quarenta recursos novos por locale elevam os catálogos regionais a 919 mensagens. Os papéis e tipos de unidade reutilizam a terminologia web nos locales correspondentes, preservando os códigos próprios de cada plataforma (web en-GB/nb-NO; Flutter en_US/no_NO). Helpers retornam somente labels e mantêm valores desconhecidos opacos. As sete opções de perfil e os três tipos existentes continuam iguais. Códigos, empresa, ator, vínculo com colaborador, corpo de create/update, senha segura e campos legais permanecem; perfis especiais não foram acrescentados ao seletor.

Erros locais são callbacks de apresentação no locale atual; mensagens específicas do servidor permanecem intactas. O diálogo conserva dados digitados, seleção, senha temporária e motivo de erro. Copiar senha mantém Clipboard e o aviso acompanha o idioma. Seletores com largura expandida, linhas variáveis e identificação completa por tooltip acomodam rótulos longos no celular; values e seleção não mudam. A política conserva o parse inteiro/mínimo de cinco anos, gate master_admin/general_admin e escopo company_id; as traduções estrangeiras identificam a referência brasileira/NR-6. QR conserva rawValue, guarda de repetição, lanterna e retorno do picker; só labels/tooltips mudam.

Os 36 testes direcionados passaram em cada projeto: 26 de formulários/configurações (incluindo valores desconhecidos), cinco do QR com porta de câmera simulada e cinco comparações exaustivas dos delegates base/região. Fluxos reais exercitam validação sem escrita, erro genérico/específico, create somente após save, identidade exata de payload/Bearer, campos preservados e zero consultas ao trocar idioma. A política foi exercitada com perfil de edição e leitura, mínimo inválido, PUT explícito e falha de carregamento. Os testes não certificam RBAC real ou câmera nativa. Os 52 guards dirigidos de identidade/entrega/paridade passaram em cada produto. Analyzer dos três arquivos novos sem apontamentos; as quatro views mantêm sete infos preexistentes. Quinze entradas migradas saíram da allowlist; catálogo/gate/paridade passaram com 298 arquivos sincronizados.

A revisão independente comparou por AST chamadas API e regras selecionadas nas quatro views, sem desvio material nesse recorte; conferiu 200 textos/parametrizações sem bloqueio linguístico material. Não executou o runtime deste bloco. Capturas de usuários/retenção mostram antes/depois FR em 390×844 com fontes reais e fixture idêntico, sem erros ou escrita. A tradução não certifica fundamento jurídico da retenção.

O inventário independente Flutter adicional está em audit/FLUTTER_GAP_INVENTORY_AUDIT.md: 219 arquivos app/design/API adjacente, 4.774 expressões e 117 ocorrências com sink confirmado (109 prosa e oito valor/label dual). São ocorrências de um recorte estático, não dívida total, mensagens únicas nem cobertura integral. Os CSVs identificam defaults, dados/códigos, produtores/sinks e 16 rastros com contraexemplos. Há lacunas em arquivamento, detalhes de EPI, períodos, notificações, rótulos de modelos e erros; permanecem pendentes. O scanner é Corporate; a paridade das superfícies alteradas foi verificada separadamente.

Backend CI aprovou 46fd5d67/d000861 após a correção da guarda estática de entrega; Flutter CI aprovou as árvores de produto anteriores 5baea4bc/3010613f. Este novo bloco precisa de CI próprio. Implementação integral e integração UBX/main continuam abertas. READY FOR HUMAN MERGE DECISION: NO.

## Continuação — Flutter: arquivamento, detalhes e apresentações restantes

O bloco acrescenta **64 recursos**, totalizando **983 mensagens** em cada catálogo regional, com os cinco aliases sincronizados e delegates oficiais. Arquivamento/restauração de Colaboradores, EPIs e Unidades inclui títulos, explicações, estados vazios, datas, retenção/plurais e menus já abertos. Seis diálogos agora permitem scroll para traduções longas no celular; isso corrige um overflow preexistente exposto a 390×844/escala 1,3 sem mudar ações ou prazo. Os textos de confirmação conservam o mínimo configurado anterior; não foi acrescentada fundamentação legal.

Detalhes de colaborador/EPI, dias, competência da ficha, pendências, condições de devolução e notas/filtros de estoque usam apresentação localizada. O mês é formatado na UI a partir do período canônico; o modelo e seus dados não são regravados. Valores desconhecidos de enum/responsabilidade permanecem intactos; `other_contracted` mantém seu código e ganha o rótulo correto. As seis responsabilidades continuam com os mesmos valores persistidos em português, traduzidos somente para exibição.

Visibilidade de módulos preserva a lista de códigos, perfis, herança e POST por empresa/Unidade, incluindo o gate de leitura/edição. Cadastro de empresa conserva os planos/minUsers, CNPJ, destinatário de convite e corpo de criação; os perfis do texto são compostos a partir dos recursos oficiais existentes. Validação acompanha o idioma sem apagar campos ou reenviar. Notificação local de estoque usa metadado aditivo de contagem, sem mudar classificação ou dados FCM; notificações remotas continuam opacas. Detalhes específicos de backend são preservados e permanecem na dívida global de internacionalização.

Passaram **19 novos testes** de widgets/apresentação, além da suíte inteira do app: **572/2 pulados no Corporate e 548/2 no SaaS**. As provas mudam os cinco idiomas com popup/diálogo aberto, campos e motivos preenchidos, verificam payload/ator/Bearer, ausência de refetch/escrita durante a troca, estados vazios, falha de carga/leitura da configuração, plurais 0/1/2/1.234 e valores desconhecidos. Pacotes de design e catálogos passaram 39 e cinco testes. Guards Python direcionados: 184 em cada projeto. Manifesto de paridade ampliado para 299 arquivos; sete entradas migradas foram removidas das allowlists, preservando diferenças históricas só de comentário.

Revisão independente parcial: quatro provas próprias aprovadas, incluindo cadastro de empresa, notificações opacas/localizadas e diálogo móvel. Achados de rótulo canônico, estados vazios, menus antigos, perfis e overflow foram corrigidos. Fontes/manifestações em `flutter-remaining-message-sources.json`, `audit/FLUTTER_REMAINING_REVIEW.md` e `audit/FLUTTER_REMAINING_CATALOGUE_REVIEW.json`. Capturas antes/depois reais de empresa em FR/390×844, com fonte local e fixture igual, ficam em `evidence/remaining-surfaces/`; não são teste de dispositivo nativo. Os fontes congelados de captura são apenas evidência histórica.

**A tarefa integral continua aberta. READY FOR HUMAN MERGE DECISION: NO.** Restam a revisão global de mensagens/erros dinâmicos backend, documentos/superfícies remanescentes, matriz integral e integração com a main/UBX atual. Nenhum conflito foi resolvido por substituir um lado inteiro; nenhuma branch de outro agente foi alterada. Este bloco terá seus próprios HEADs e CI vinculados nos PRs #1060/#434. Sem merge, deploy, force-push ou alterações em bancos compartilhados.

A primeira Backend CI deste bloco (Corporate `2a9bc778`, SaaS `2f0bb527`) expôs um guard de menu que só reconhecia a tupla Dart em uma linha. A permissão `legal_entities:view` permaneceu no quarto campo. A falha foi reproduzida nos dois projetos (sete testes aprovados e um reprovado) e o matcher passou a aceitar whitespace entre os campos, exigindo rota, dois ícones e permissão nessa ordem. Os oito testes passaram em ambos após o ajuste; a nova revisão independente e CI são vinculadas nos PRs, sem mudança de lógica do produto.

No Corporate, o guard preexistente de logout também exigia o literal português `Sair`. Foi reproduzido (dois aprovados/um reprovado) e passou a exigir o recurso localizado `passwordChangeLogout`, mantendo as verificações de posição na AppBar e chamada de `AuthCubit.logout()`. Seus três testes passaram após o ajuste. O teste não existe na branch SaaS; não houve alteração adicional de produto.


## Integração das branches dos PRs com a main — 30/10/2026

Os conflitos mostrados nos PRs #1060/#434 foram conciliados nas branches de trabalho com a main Corporate `776d516d` e SaaS `df453a5`. A estrutura UBX-V5 prevalece para a propriedade das funções; cinco funções extraídas recebem os bindings de apresentação da I18N. Todos os recursos dos dois lados foram preservados, sem substituir o catálogo inteiro por uma versão. A correção de Situação da Empresa conserva `active` como `1/0`, sem `data-i18n-value` nas opções. Index e digests são regenerados a partir das fontes conciliadas.

A revisão independente encontrou dois defeitos de apresentação preexistentes: interpolação externa ao binding da dica Joint Venture e uso de navegação/refresh de dados na troca de idioma. Ambos foram reproduzidos e corrigidos. A nova prova engine+módulo conserva nome e trava de unidade nos cinco idiomas. A prova Chromium de Colaboradores mantém rascunho, ID, unidade/CNPJ, estados disabled e aba ativa durante cinco trocas, sem novas consultas de dados ou escritas. A resposta do fixture de locale foi atualizada para o contrato `locale`/`translations`, e o relatório vazio usa a estrutura real; não houve mudança de API para satisfazer o fixture.

Os testes de caracterização continuam comparando permissões, corpos, IDs e fluxos, passando a exigir os novos bindings de tradução. A guarda UBX passou sem novas responsabilidades/endpoints no monólito. O relatório `UBX-INTEGRATION.json` descreve esta integração e seus limites; os resultados finais por HEAD serão vinculados aos PRs. As quatro CIs Backend/Flutter do checkpoint anterior `8a0ded84`/`3b016875` passaram e estão registradas em `CI-RESULTS.json`; não substituem a CI pós-integração.

A internacionalização integral continua em andamento. READY FOR HUMAN MERGE DECISION: NO. Os PRs permanecem draft, sem merge dos PRs na main, deploy, force-push ou escrita em bancos compartilhados.

A main avançou durante a validação com SECURITY-OUTPUT-XSS-V1 (Corporate `91b60160`, SaaS `decedc5`); os escapes foram conciliados com os bindings em cinco regiões do app, preservando os demais serviços/módulos de segurança. A revisão também reproduziu troca acidental de perfil/vínculo no formulário de Usuário ao mudar idioma. Os populadores agora mantêm somente seleções ainda presentes nas listas permitidas. A regressão Chromium verifica campos, perfil, vínculo e estados disabled em cinco idiomas, sem gravação nem consulta extra de dados.

A CI automática voltou a executar após a resolução dos conflitos. Secret Scan apontou 97 ocorrências históricas por produto: 94 identificadores `ui.*` de inventário e três hashes SHA-256 de fontes públicas. Cada linha foi conferida no commit histórico, e os seis hashes foram recalculados. `.gitleaksignore` mantém as duas entradas anteriores e acrescenta apenas os 194 fingerprints exatos dos dois históricos; `.gitleaks.toml`, regras e caminhos de detecção não mudam. A varredura local do histórico passou de 97 para zero achados por produto. Um segredo sintético novo no mesmo caminho continuou sendo detectado (exit 1), com resultado em `audit/GITLEAKS_NEGATIVE_RESULT.json`; não há valores de credenciais no relatório. A validação CI do próximo HEAD é registrada nos PRs.
