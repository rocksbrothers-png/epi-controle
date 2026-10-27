# Auditoria independente de documentos de Compras

Escopo: Corporate working tree posterior a `bc9cf725d52933c977d2550bb0e032221756bc4e`, módulos presentation, builders de RFQ/PO, emails de link do fornecedor e integração de locale nas rotas. Nenhuma alteração de produto ou banco; nenhum SMTP, contato externo ou entrega real de email. Esta auditoria não aprova I18N-FULL-V1 integralmente.

## Contratos preservados

`document-contract-results.json` registra hashes e comparação AST independente:

- SQL literal, chamadas de registro de auditoria e argumentos do envio/destinatário iguais à base nos quatro arquivos modificados.
- quantity/int, unit_price/float, line_total/round e soma do total da PO exatamente iguais à base. A apresentação financeira mantém `.2f` dos floats antes de aplicar separadores e BRL; não há conversão de moeda.
- As quatro rotas ficam com AST exatamente igual removendo somente import e keyword locale. Guardas de autorização/escopo permanecem antes da geração/envio.
- Geração, hash, resolução, expiração, escopo e operações dos tokens permanecem iguais. Sem locale explícito, portal_link_url mantém o URL anterior; com locale, acrescenta somente query lang, preservando o caminho e token.
- Funções de negócio fora dos builders/envio permanecem iguais. O novo Translator não recebe identidade/tenant, não consulta preferências, não escreve banco nem ativa locale global.

## Prova independente de runtime

`document-runtime-results.json` e PDFs `document-audit-*`:

- Dez PDFs reais: RFQ e PO × cinco idiomas, cada qual com 125 itens. Extração `pdftotext -layout` encontrou os 125 identificadores em cada PDF, incluindo o último item, com múltiplas páginas.
- Caracteres WinAnsi (`Équipement`, parênteses, barra) permaneceram legíveis. Sem placeholders de template em PDF. Nomes/observações contendo `{id}`, `{request}` e HTML permanecem valores originais, sem segunda interpolação. Dados de entrada intactos.
- 210 apresentações em 14 threads, alternando cinco idiomas e aliases Flutter en_US/no_NO, sem cruzamento de data, moeda ou texto. Idioma do catálogo e locale de formatação permanecem por instância.
- Float 2.675 conserva a apresentação de duas casas do contrato anterior; cálculo de total confirmado pela comparação estrutural.
- Prioridade de Accept-Language, q=0/NaN e tentativa de query inválida testadas. Query permitida tem prioridade sem alterar identidade. Locale é normalizado por whitelist, sem interpolação de caminho arbitrário no carregamento de JSON.
- Catálogo/chave solicitados ausentes falham explicitamente, sem emitir documento em PT ou chave crua. Nenhum envio ocorreu no probe.
- Cinco catálogos documents têm paridade de folhas e placeholders. CA continua brasileiro; BRL e nomes/códigos originais são preservados. Não foi confirmada cópia indevida de inglês nas frases ES/FR/NB deste recorte; termos comuns/empréstimos e identidade EPI Controle não são tratados como falha.

## Observações e limites

A cache LRU guarda apenas os cinco catálogos; não guarda o locale ativo de uma requisição. Os dicionários retornados são privados e somente lidos pelos consumidores analisados. Tradutores por instância e Babel recebem locale explicitamente. Babel consta em requirements; a prova usou a biblioteca instalada, sem testar uma instalação limpa de dependências.

O helper number do Babel usa a precisão padrão de três casas decimais. Nos builders atuais, quantidades de PO são int e RFQ usa o contrato de quantidade inteira existente; não foi identificado fluxo válido atual que exija mais casas nesse parâmetro. Se o helper passar a formatar medidas fracionárias ou valores técnicos em outros documentos, a precisão deve ser especificada e testada antes dessa expansão. Esta observação não é apresentada como alteração de cálculo ou defeito confirmado no fluxo atual.

Não foram executadas entregas SMTP, validade real de tokens ou autorização HTTP neste probe. As evidências do implementador com MailSpy/banco em memória complementam, mas não são apresentadas como execução independente. Outros documentos, recibos, exportações, relatórios e Flutter permanecem fora deste bloco. A revisão deve ser reconfirmada contra os HEADs finais e paridade Corporate/SaaS quando o bloco for commitado.
