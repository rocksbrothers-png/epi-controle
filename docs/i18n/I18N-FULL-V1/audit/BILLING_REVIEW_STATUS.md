# Billing Flutter — revisão independente parcial entregue

O implementador validou as duas telas e os formatadores nos cinco locales, com dados sintéticos e transportes interceptados. Foram aprovados 28 testes direcionados em cada produto, incluindo filtros canônicos, confirmação explícita antes de cancelar, mensagens de erro, ausência de dados, URLs originais de recibos e valores BRL. A prova de recibos usa uma porta de plataforma simulada; não abriu um recibo real.

A revisão independente interrompida por limite de uso foi retomada e concluída para este recorte. Os quatro testes externos passaram: arredondamento BRL/data, filtro pending/URL opaco, confirmação antes do POST/reason vazio/SnackBar e os 14 indicadores tipados. Os relatórios FLUTTER_BILLING_AUDIT.md e FLUTTER_BADGES_AUDIT.md registram as leituras de contrato, resultados e limites. As correções linguísticas posteriores foram conferidas em fonte pelo auditor; os CIs e testes do implementador validam a redação final. Isso não é auditoria final de I18N-FULL-V1 nem certificação de RBAC real.

PIX e os nomes comerciais dos planos permanecem originais. IDs de empresa, tenant e Mercado Pago, URLs e códigos externos desconhecidos são dados opacos. Boleto é identificado como o instrumento brasileiro nas traduções estrangeiras; não foi convertido em outro meio de pagamento.

As capturas usam o widget de faturas de 454bee68 como baseline, com import/classe adaptados no harness, e o widget atual. Ambos recebem o mesmo fixture sintético em fr_FR, 390×844, Inter/EpiTheme/MaterialIcons. Não são capturas de uma implantação histórica nem uma execução Android/iOS. O JSON registra o fixture, ausência de escrita e erros de layout. A internacionalização integral segue incompleta e READY permanece NO.
