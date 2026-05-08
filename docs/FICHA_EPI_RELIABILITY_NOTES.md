# Ficha de EPI — Notas de Confiabilidade (Consolidação Preventiva)

## 1) Cobertura visual real de browser

No estado atual do repositório não há infraestrutura E2E/browser (Playwright/Cypress) pronta.
Para manter baixo risco e evitar introduzir stack nova agora, a consolidação foi feita com testes automatizados de saída HTML do renderer unificado, cobrindo:

- estrutura base da ficha;
- presença de blocos de impressão (`@page`, tabela, coluna de assinatura);
- cenário de ficha por período sem mistura de itens de outros períodos.

**Próximo passo recomendado (futuro, controlado):** adicionar runner E2E leve (ex.: Playwright) somente para 3 cenários críticos: visualizar ficha, imprimir ficha, snapshot histórico.

## 2) Políticas de tentativas separadas

A política permanece separada intencionalmente entre:

- `employee_portal_links` (com contador/bloqueio de tentativas);
- `users.employee_access_token` (fluxo legado, preservado por compatibilidade).

A separação foi mantida para não quebrar tokens existentes. O código possui comentário explícito nesse ponto e testes cobrindo:

- sucesso e bloqueio no fluxo `employee_portal_links`;
- compatibilidade do fluxo legado `users.employee_access_token`.

**Preparação para unificação futura:** quando a migração de tokens legados for planejada, extrair política comum em camada interna sem alterar contrato externo em uma única etapa.
