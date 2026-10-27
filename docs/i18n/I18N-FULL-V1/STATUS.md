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
