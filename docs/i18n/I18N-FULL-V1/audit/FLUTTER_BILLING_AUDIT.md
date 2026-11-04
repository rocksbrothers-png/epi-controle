# Auditoria independente — billing Flutter

Escopo: alterações de apresentação posteriores a Corporate `454bee68`, incorporadas no checkpoint `c1faf3a3` / SaaS `272697a9`; execução independente no Corporate. Não inclui FeedbackScreen nem certifica internacionalização integral.

## Resultado restrito

Nenhum novo defeito de contrato confirmado. APIs/modelos de subscription, ApiClient e SessionContext estão byte a byte iguais à base em `flutter-billing-static-results.json`. Filtros, cancelamento, autenticação, empresa/tenant e URLs de recibos permanecem preservados. A correção de Flexible no valor de invoice passou na prova real de UI em 390×844 com BRL 12.345.678,90.

## Evidência independente

`flutter-billing-badges-runtime-final.log`: quatro testes passaram no harness externo; três cobrem diretamente este recorte, o quarto é de badges. `flutter-billing-badges-runtime-results.json` contém requests e resultados.

- Formatação em cinco locales: conserva o resultado de `double.toStringAsFixed(2)` para 2.675, símbolo/código BRL sem FX e a mesma data de calendário da parte inicial do ISO, sem conversão de fuso. Data inválida permanece opaca. A primeira execução do teste puro falhou porque o harness não inicializava Intl date data fora de MaterialApp; corrigiu-se apenas o harness. Não foi falha de rounding ou de produto.
- InvoicesScreen real: filtro pending mantém o código e a seleção após EN→FR. A troca de locale não refaz GET. Valor grande cabe em 390×844, sem exceção/overflow. Apenas GETs; Bearer sintético preservado. Recibo abre externamente com URL exatamente `https://synthetic.local/receipt?original=00123&literal=A%2FB`, sem acrescentar idioma, token, empresa ou novos parâmetros.
- SubscriptionScreen real: diálogo aberto retraduz EN→FR e FR→NO. Zero POST antes de confirmação; Voltar continua sem POST. Confirmação explícita gera exatamente um POST `/api/subscriptions/cancel` com `{'reason':''}` e Bearer sintético. Snackbar de sucesso retraduz após a mudança subsequente para francês, sem novo POST.

## Inspeção de contratos e linguagem

Status de filtro continuam null/paid/pending/cancelled/refunded/failed; aliases de exibição canceled/cancelled e active/authorized conservam os caminhos existentes. `_cycleLabel` continua com o mesmo fallback mensal. `_future` permanece em estado, carregado por init/ações explícitas. Plano, identificadores de tenant/empresa/MP e detalhes de erro não são traduzidos como dados.

O cancelamento continua exigindo `confirmed == true`, conserva busy/mounted/reload e delega ao mesmo método sem argumento, cujo reason default é vazio. O URL opaco e LaunchMode.externalApplication não foram alterados. Dialog e SnackBars consultam locale no próprio contexto dependente, sem congelar a tradução inicial em string de estado.

Os cinco catálogos têm 41 recursos novos de billing. Recomendações linguísticas francesas e limites de termos de pagamento constam em `FLUTTER_LINGUISTIC_REVIEW_PARTIAL.json`; são recomendações de apresentação, sem mudança de códigos/valores.

## Limites

Só transporte e dados locais; nenhum cancelamento real, pagamento, fornecedor, banco ou host externo. Não se reexecutou todo o conjunto de 28 casos informado pelo root. Mensagens específicas de ApiException permanecem opacas e dependem do recorte global de erros backend. Não há aprovação integral, merge/deploy ou certificação de RBAC real. A execução não usou pubget, format ou restauração dos arquivos de ferramenta.

## Atualização de redação conferida sem SDK

As seis sugestões FR de billing foram aplicadas pelo root e verificadas em fonte: Actif/Résilié/Expiré, Carte (paiement récurrent), Prochain paiement e Dernier paiement. Os resultados de runtime acima permanecem históricos ao passo anterior de redação; nenhum novo Flutter foi executado pelo auditor após essa atualização. Os contratos e valores não foram alterados por essas palavras.
