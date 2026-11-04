# Exposição real das mensagens backend — auditoria independente

O inventário inicial contém 1.194 ocorrências de `raise` e 982 templates únicos. Ele não contém todas as mensagens devolvidas diretamente em JSON ou persistidas como status. Nesta revisão, 219 arquivos foram analisados por AST, sem importar a aplicação, conectar bancos ou executar workers.

## Classificação e rastreabilidade

`backend-template-exposure.json` contém os 982 templates, cada ocorrência, símbolo, caminhos estáticos até entradas e limitações. Resumo revisado: 863 alcançáveis por rotas; 8 por worker; 10 por inicialização do servidor; 101 sem resolução estática. Entradas CLI também são registradas como eixo de alcance, sem presumir exclusividade. A primeira versão rotulava dez entradas como CLI; o refinamento identifica também o alcance pela inicialização do app, portanto não são dispensadas por suposto uso apenas em CLI.

`backend-template-exposure-prioritized.json` agrega consumidor e correspondências exatas no catálogo PT. Prioridades: 158 templates do domínio Compras; 8 dos conectores dinâmicos; 72 da Biblioteca; 634 de outras rotas; 8 do worker de migração; 10 operacionais de inicialização; 92 ainda sem consumidor identificado nesta triagem. As categorias são prioridades, não contagens de mensagens efetivamente vistas. Apenas 83 templates têm algum valor PT exatamente igual no catálogo atual; isso não prova tradução em execução nem mede cobertura integral.

## Dezessete fluxos revisados

Os caminhos/linhas/excertos e consumidores estão em `backend-exposure-reviewed-flows.json`.

1. Os wrappers HTTP globais retornam `str(exc)` em 400/403 e também em 500. Assim, exceptions de serviços chamadas pelas rotas podem chegar à UI, mesmo se também forem registradas em log. Erros de integridade são transformados por `humanize_integrity_error`: priorizar a saída amigável, não o SQL original.
2. Biblioteca: ValueError do worker vai a `error.json`, é relançado por preview e devolvido pela rota como `error`. A categoria worker não dispensa tradução. Erros internos não ValueError do conversor são substituídos por aviso genérico; o texto interno não precisa ser exposto. Cliente atual chama describeApiError e mantém metadados para retradução. A prova congelada em Chromium confirma uma mensagem real desse caminho.
3. Recebimento de Compras: JSON inclui `error` e `validation` com código/linha/item. Código genérico não deve apagar o detalhe. O cliente central agora reconhece validation.code, mas o consumidor deve conservar error.i18n quando precisar de troca de idioma ao vivo.
4. Procurement: helper privado usa fetch direto, extrai error.message/error e os consumidores exibem via toast ou textContent. Não passa pelo novo cliente central. Catálogos adicionais, isoladamente, não traduzem esse fluxo ativo.
5. Checkout: postJson próprio extrai nested error.message e exibe em showResult(String(err)); ignora describeApiError. Preserve o Bearer/nonce Corporate e capability SaaS ao conectar a apresentação. Falhas de persistência substituem o erro interno por CHECKOUT_PERSIST_PENDING e instrução de mesma idempotency_key; traduzir sem alterar a orientação de retry. Webhook é comunicação de máquina com provedor, sem consumidor de negócio comprovado.
6. Portal do fornecedor: HTML independente atribui mensagens de erro diretamente ao textContent em envio de cotação/confirmação. Possui contexto e token próprios; a engine do painel não cobre essa página.
7. Portal do colaborador: o fluxo no painel delega primeiro a globalThis.api. O fetch cru é fallback fora do app; não classificar o fluxo principal como bypass sem prova. No fallback, error objeto pode virar [object Object].
8. Conectores: fábrica dinâmica não é resolvida pelo grafo simples. Revisão manual confirma get_connector → connector.get_catalog/ping → ConnectorError incorporado em ValueError → rota → feedback de Procurement. Sete templates HTTP e um de registro/fábrica estavam entre os unresolved e continuam prioridade real. Não dispensar esses casos por ausência de aresta estática.
9. Migração assíncrona: erros de autorização, descriptografia e transação são substituídos por três mensagens genéricas persistidas, e `_public` preserva error_message no GET/list de jobs. Traduzir a apresentação do status, sem expor payload ou mensagens internas. Não foi encontrado consumidor Web/Flutter ativo dessa API no inventário anterior; isso permanece uma limitação, não uma isenção definitiva.
10. Histórico da migração síncrona: erro legado e diagnóstico histórico são substituídos por mensagens públicas fixas; priorizar esses avisos e os erros por registro, preservando os códigos.

## Limites

Alcance estático não equivale a propagação de exceção: catches podem substituir, suprimir ou registrar o erro. Callbacks produzem aproximação conservadora e dispatch dinâmico pode não ser resolvido. As 101 lacunas estáticas permanecem explícitas, mesmo quando oito conectores receberam evidência manual adicional. Não há afirmação de que todos os 863 templates sejam UI, nem de cobertura concluída dos demais. Flutter e todos os sinks restantes exigem análise/provas específicas.


## Atualização — conectores de Compras

A pendência dinâmica HTTP/fábrica do item 8 ganhou um bloco de apresentação comprovado no modal Web: oito erros de conector/fábrica, três guardas de integração, cinco wrappers e um 404, mais dois rótulos conhecidos. A classificação de exposição inicial foi preservada acima como histórico; não é uma lista de pendências atualizada automaticamente. `CONNECTORS_REVIEW.md` e `CONNECTORS-CHECKPOINT.json` delimitam a cobertura e os testes antes/depois. A inexistência de consumidor Flutter para estes endpoints foi pesquisada; não se afirma tradução genérica do backend ou cobertura de outros consumidores.
