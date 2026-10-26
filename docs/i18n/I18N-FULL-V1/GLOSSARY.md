# Glossário técnico — cinco idiomas existentes

| Conceito | pt-BR | en-GB | es-ES | fr-FR | nb-NO |
|---|---|---|---|---|---|
| EPI | Equipamento de Proteção Individual (EPI) | Personal Protective Equipment (PPE) | Equipo de Protección Individual (EPI) | Équipement de protection individuelle (EPI) | Personlig verneutstyr (PVU) |
| Certificado brasileiro | CA — Certificado de Aprovação | Brazilian Approval Certificate (CA) | Certificado de aprobación brasileño (CA) | Certificat d’approbation brésilien (CA) | Brasiliansk godkjenningssertifikat (CA) |
| Identificador brasileiro | CPF brasileiro | Brazilian CPF | CPF brasileño | CPF brésilien | Brasiliansk CPF |
| Peça física | Peça física | Physical item | Pieza física | Pièce physique | Fysisk enhet |
| Lote | Lote | Batch | Lote | Lot | Parti |
| Validade física | Validade física | Physical expiry | Caducidad física | Péremption physique | Fysisk utløpsdato |
| Requisição | Requisição de compra | Purchase requisition | Solicitud de compra | Demande d’achat | Innkjøpsrekvisisjon |
| Cotação | Cotação | Quotation | Cotización | Devis | Tilbud |
| Pedido de compra | Pedido de compra (PO) | Purchase order (PO) | Pedido de compra (PO) | Bon de commande (PO) | Innkjøpsordre (PO) |

O campo atual contém um CA brasileiro. Não existe equivalência jurídica automática com a marcação CE e nenhuma tradução cria um número CE. Um futuro suporte regulatório europeu requer campos e regras próprios, em proposta separada.

CPF continua sendo o identificador brasileiro administrado pela Receita Federal. NIF/NIE (Espanha), numéro fiscal (França), NINO/UTR (Reino Unido) e fødselsnummer/D-nummer (Noruega) são referências contextuais, não novos nomes para CPF. NIF português, Codice Fiscale italiano, IdNr alemão e SSN/ITIN americano também não são intercambiáveis com CPF. Suporte real a documentos estrangeiros exige proposta separada com país emissor, tipo, validação e tratamento de dados; isso não é implementado neste trabalho.

Web mantém `pt-BR`, `en-GB`, `es-ES`, `fr-FR`, `nb-NO`. Flutter mantém `pt_BR`, `en_US`, `es_ES`, `fr_FR`, `no_NO` e seus aliases preexistentes. Diferenças de código regional não criam novos idiomas nem autorizam alterar dados persistidos.
