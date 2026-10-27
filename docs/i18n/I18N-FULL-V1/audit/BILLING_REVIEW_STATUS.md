# Billing Flutter — revisão independente pendente

O implementador validou as duas telas e os formatadores nos cinco locales, com dados sintéticos e transportes interceptados. Foram aprovados 28 testes direcionados em cada produto, incluindo filtros canônicos, confirmação explícita antes de cancelar, mensagens de erro, ausência de dados, URLs originais de recibos e valores BRL. A prova de recibos usa uma porta de plataforma simulada; não abriu um recibo real.

A revisão independente começou com observações estáticas: filtros null/paid/pending/cancelled/refunded/failed, cancel() depois de confirmed == true, reason padrão vazio, Bearer, URI e LaunchMode originais, IDs opacos, arredondamento .2f e data de calendário preservados. A execução do agente foi interrompida por limite de uso antes do relatório consolidado e de prova de runtime própria. Essas observações não constituem auditoria final aprovada. A revisão independente deste recorte permanece pendente; as auditorias históricas de alertas/formulários conservam seus escopos e SHAs.

PIX e os nomes comerciais dos planos permanecem originais. IDs de empresa, tenant e Mercado Pago, URLs e códigos externos desconhecidos são dados opacos. Boleto é identificado como o instrumento brasileiro nas traduções estrangeiras; não foi convertido em outro meio de pagamento.

As capturas usam o widget de faturas de 454bee68 como baseline, com import/classe adaptados no harness, e o widget atual. Ambos recebem o mesmo fixture sintético em fr_FR, 390×844, Inter/EpiTheme/MaterialIcons. Não são capturas de uma implantação histórica nem uma execução Android/iOS. O JSON registra o fixture, ausência de escrita e erros de layout. A internacionalização integral segue incompleta e READY permanece NO.
