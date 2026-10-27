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
