# I18N-FULL-V1 — implementação em andamento

Este é um checkpoint de implementação, não uma certificação de cobertura integral.

## Etapas

- A: inventário inicial registrado em `inventory-A.json` e `inventory-A.csv`.
- B: bindings estáticos e grande parte dos fluxos dinâmicos de Compras implementados; revisão de mensagens, formatação, portal do fornecedor e documentos ainda em andamento.
- C: 907 ocorrências do inventário HTML inicial receberam bindings. As 112 ocorrências técnicas restantes estão enumeradas e justificadas em `html-exceptions.json`. O JavaScript dinâmico dos demais módulos continua em revisão.
- D: CA brasileiro e CPF identificados explicitamente nos rótulos web e Flutter. Revisão linguística/glossário completo e demais textos Flutter ainda pendentes.
- E: testes direcionados e revisão independente parciais. Navegação integral em cinco idiomas, matriz funcional final, paridade e CI finais ainda pendentes.

Os valores em reais permanecem BRL. A tradução não converte moedas, CA/CE ou documentos pessoais. Valores canônicos de motivos, permissões, IDs, linhas assinadas e decisões da associação são preservados.

A geração de novos PDFs declara a codificação WinAnsi e escapa o texto uma única vez. Documentos históricos assinados, snapshots, contratos já emitidos e arquivos originais da Biblioteca permanecem no idioma original e não são retraduzidos, regravados nem reassinados.

## Veredito deste checkpoint

- TECHNICAL VERDICT: não emitido; implementação incompleta.
- GOVERNANCE VERDICT: validação final pendente.
- READY FOR HUMAN MERGE DECISION: NO.
