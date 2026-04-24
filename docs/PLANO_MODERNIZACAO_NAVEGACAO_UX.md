# Plano de modernização de navegação e UX (zero regressão)

## 1) Diagnóstico do cenário atual

### O que existe hoje
- O frontend já funciona como **multipage simulada dentro de uma única página** (`index.html`) com blocos `<section class="view">` alternados por JavaScript. Isso reduz recarregamento total, mas concentra muitas responsabilidades em um único arquivo grande.  
- A navegação principal depende de botões `.menu-link` que chamam `showView()`; o mecanismo ativa/desativa telas via classe `active`.  
- Há uma base visual válida (sidebar, topbar, cards, grid), com bom ponto de partida para evoluir para padrão SaaS.

### Gargalos de UX observados
- **Acoplamento alto de UI**: a aplicação concentra renderizações e eventos em um JS monolítico, tornando evolução lenta e com risco operacional se não houver estratégia incremental.
- **Contexto de navegação limitado**: não há breadcrumbs, URL por estado de tela e histórico robusto de navegação (back/forward do navegador).
- **Feedback inconsistente**: coexistem `alert/confirm` e toast/modal; isso reduz sensação de produto profissional.
- **Descoberta de fluxo**: telas funcionam, porém o usuário pode sentir “ilhas funcionais” quando alterna módulos sem contexto persistente.

### Limitações da abordagem atual
- Sem camada declarativa para interações locais (mostrar/ocultar, estados pequenos, loading por componente), o JS global tende a crescer de forma rígida.
- Sem fragmentação de render server-driven, toda evolução tende ao padrão “editar arquivo JS central”, com maior risco de regressão visual.

---

## 2) Escolha de tecnologia de navegação (decisão arquitetural)

## Opções avaliadas
1. **HTML + JS puro (incremental)**
   - Prós: sem nova dependência, controle total.
   - Contras: mantém acoplamento alto; curva de manutenção piora com o tempo.

2. **HTMX (recomendado para Python)**
   - Prós: navegação parcial e carregamento incremental via HTML server-driven; baixa intrusão; ótimo para apps Python com templates/rotas existentes.
   - Contras: exige disciplina para contratos de fragmentos e padrão de eventos.

3. **Alpine.js isolado**
   - Prós: excelente para microinterações locais.
   - Contras: não resolve sozinho navegação server-driven e composição de telas.

4. **SPA React/Vue**
   - Prós: maior capacidade de UI complexa.
   - Contras: maior risco de regressão, necessidade de camada API mais formal, reestruturação ampla, aumento de custo operacional.

## Decisão recomendada
**Escolha: Opção 2 (HTMX) + Alpine.js como complemento de microinteração.**

### Justificativa para seu cenário
- Mantém backend Python e rotas atuais intactos (camada adicional, não substitutiva).
- Entrega UX “quase SPA” com baixo risco de regressão.
- Funciona muito bem em Render (é apenas web app tradicional com HTML/JS/CSS).
- Evita custo e risco de uma migração total para SPA.

---

## 3) Estratégia de implementação (não invasiva e incremental)

## Princípios de zero regressão
- **Não alterar regras de negócio**: endpoints e validações atuais permanecem fonte da verdade.
- **Não alterar permissões nem banco**: somente camada de apresentação/interação.
- **Feature flags de frontend**: ativar melhorias gradualmente por rota/tela.
- **Fallback obrigatório**: se HTMX falhar, fluxo atual continua funcionando.

## Fases sugeridas

### Fase 0 — Baseline e segurança
1. Congelar comportamento atual com checklist de fluxos críticos (EPI, entrega, ficha, QR, contratos, relatórios, permissões).
2. Criar suíte de regressão de UI (smoke) com cenários-chave.
3. Introduzir telemetria simples de navegação (tempo por troca de tela, erro de carregamento parcial).

### Fase 1 — Casca SaaS (layout e navegação global)
1. **Shell de aplicação**: sidebar fixa + topbar + área central de conteúdo.
2. **Breadcrumbs dinâmicos** por módulo e submódulo.
3. **URL navegável** por estado de tela (`/app?view=estoque` ou hash), preservando deep-link.
4. **Botão voltar padronizado** e compatível com histórico do navegador.

### Fase 2 — Navegação parcial com HTMX
1. Converter telas prioritárias para carregamento por fragmentos HTML (sem full reload).
2. Aplicar `hx-get`, `hx-target`, `hx-swap` em listas e detalhes.
3. Manter endpoints atuais; quando necessário, criar endpoints de fragmento sem tocar regra de negócio.

### Fase 3 — Interatividade moderna
1. Trocar `alert/confirm` por **modal de confirmação** padrão.
2. Padronizar **toast/snackbar** para sucesso/erro.
3. Inserir **loading states** por componente (botão, tabela, card).
4. Formulários com validação visual e envio assíncrono progressivo.

### Fase 4 — Polimento SaaS
1. Dashboard com cards de KPIs + ações rápidas.
2. Ferramentas de filtro/busca sempre visíveis em listas críticas.
3. Consistência visual (tipografia, espaçamento, estados de botão, feedback).

---

## 4) Padrões práticos para aplicar no seu sistema

## 4.1 Navegação sem reload completo
Exemplo de menu com HTMX (camada adicional):

```html
<button
  hx-get="/ui/fragments/estoque"
  hx-target="#app-content"
  hx-swap="innerHTML"
  hx-push-url="true"
  class="menu-link"
>
  Controle de Estoque
</button>
```

> Se esse fragmento não carregar, manter fallback para `showView('estoque')` do fluxo atual.

## 4.2 Breadcrumbs de contexto
- Mapa simples em frontend:
  - Dashboard
  - Estoque > Movimentações
  - Entregas > Nova entrega
  - Ficha de EPI > Colaborador

Componente deve atualizar ao trocar view e ao abrir detalhe/modal.

## 4.3 Modais ao invés de novas páginas
- Edição rápida, confirmação e detalhes curtos em modal.
- Persistir operações críticas em telas atuais quando risco de erro for maior.

## 4.4 Feedback unificado
- `toast.success("Entrega registrada")`
- `toast.error("Falha ao salvar")`
- `confirmDialog("Confirmar baixa de estoque?")`

## 4.5 Tabelas dinâmicas
- Atualização parcial de `<tbody>` após ação.
- Manter filtros no topo com estado persistido em query string.

---

## 5) Integração com backend Python (sem mexer em regra)

## Como integrar sem risco
- Backend continua validando tudo (permissões, regras, transações).
- Frontend passa a pedir fragmentos HTML para render parcial.
- Endpoints existentes continuam em uso para operações de negócio.

## Padrão de endpoint incremental
- `/api/...` (já existente): permanece para dados e operações.
- `/ui/fragments/...` (novo, opcional): entrega HTML parcial para HTMX.

> Isso evita reescrever backend e preserva contrato funcional atual.

---

## 6) Compatibilidade com Render

A estratégia proposta é 100% compatível com Render porque:
- Mantém app web Python padrão (sem runtime adicional obrigatório de SPA).
- Não exige infraestrutura mobile nem WebSocket para começar.
- Mantém deploy atual com assets estáticos + servidor Python.

Boas práticas no Render:
- Cache-control para assets versionados.
- Compressão gzip/brotli (quando disponível no stack).
- Healthcheck inalterado.

---

## 7) Plano de validação sem regressão

## Matriz de testes obrigatória
1. **Fluxos críticos**: entrega de EPI, ficha, QR code, contratos, relatórios.
2. **Permissões por perfil**: visibilidade e bloqueio de ações.
3. **Paridade funcional**: mesma ação, mesmo resultado de negócio (antes/depois).
4. **Navegação**: tempo de troca de tela, back/forward, deep-link.
5. **Falha controlada**: desabilitar HTMX e garantir funcionamento legado.

## Critérios de aceite
- Zero mudança em regra de negócio.
- Zero mudança em banco e permissões.
- Melhora mensurável de UX (tempo de navegação e cliques por tarefa).
- Rollback simples por feature flag.

---

## 8) Roadmap sugerido (30/60/90 dias)

- **30 dias**: shell SaaS + breadcrumbs + feedback unificado + URL de navegação.
- **60 dias**: HTMX em 2 módulos críticos (ex.: estoque e entregas) + modais padronizados.
- **90 dias**: expansão para demais módulos + otimização de performance + refinamento visual final.

---

## 9) Recomendação final

Para o seu cenário real (Python no Render, sistema já em produção e exigência rígida de zero regressão), a melhor arquitetura é:

**HTMX como motor de navegação parcial + Alpine.js para microinteração + preservação total do backend e contratos atuais.**

É a opção com melhor equilíbrio entre:
- ganho rápido de UX profissional,
- baixo risco técnico,
- compatibilidade plena com Render,
- sustentabilidade de evolução sem reescrita.
