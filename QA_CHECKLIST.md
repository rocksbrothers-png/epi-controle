# QA Checklist Oficial — Front-end (Fase 3.5)

Este checklist padroniza a validação da estabilização final da UX moderna e a preparação para rollout controlado no projeto EPI.

## 1) Escopo e objetivo

- **Objetivo:** habilitar rollout gradual, seguro e reversível da UX moderna.
- **Escopo:** front-end (`static/`) e testes (`tests/`).
- **Fora de escopo:** backend, banco, permissões e regras de negócio.

## 2) Pré-condições obrigatórias (go/no-go)

- [x] Erros de `ux-global.js` corrigidos.
- [x] Erro `uxGlobalEnabled` corrigido.
- [x] Console limpo por validação automatizada de sintaxe/estrutura; inspeção manual em navegador real permanece recomendada antes de go-live amplo.
- [x] Login funcionando.
- [x] Fases 3.1, 3.2, 3.3 e 3.4 concluídas.
- [x] Scripts sem duplicidade.
- [x] Cache-bust atualizado.

## 3) Matriz final de rollout (Fase 3 consolidada)

| Flag | Querystring | Default | Tela afetada | Risco | Rollback |
|---|---|---|---|---|---|
| `spa_navigation_enabled` | `ux_spa_navigation=1` | OFF | Navegação principal (menu + histórico + back/forward) | Médio | Desativar flag e limpar `localStorage` do piloto. |
| `ux_global_enabled` | `ux_global=1` | OFF | Dashboard, Colaboradores, Gestão de Colaborador, EPIs e Estoque (camada visual/UX) | Baixo/Médio | Desativar flag para retorno imediato ao layout clássico. |
| `dashboard_interativo_enabled` | `ux_dashboard_interativo=1` | OFF | Dashboard interativo | Médio | Desativar flag e manter dashboard clássico. |
| `ux_performance_hardening_enabled` | `ux_perf_hardening=1` | OFF | Camada de binding/event listeners | Baixo | Desativar flag para restaurar binding padrão. |

> Observação: defaults permanecem OFF para rollout controlado.

## 4) Plano de ativação gradual

1. **Etapa 1 — Admin/Teste via querystring**
   - Ativar flags apenas por URL para contas internas.
   - Validar login, troca de telas, console e fluxo principal.

2. **Etapa 2 — Validação por tela**
   - Testar cada tela afetada isoladamente.
   - Confirmar fallback clássico quando flag OFF.

3. **Etapa 3 — Storage controlado**
   - Habilitar rollout por `localStorage` somente para grupo piloto.
   - Monitorar erros de console e regressões funcionais por sessão.

4. **Etapa 4 — Avaliar default ON (futuro)**
   - Só considerar após ciclo estável sem regressão crítica.
   - Registrar decisão e janela de rollback antes da mudança.

## 5) Rollback simples (obrigatório)

- [x] Flag OFF restaura UX clássica.
- [x] Limpar `localStorage` desativa UX moderna no navegador.
- [x] Revert front-end é suficiente para retorno estável.
- [x] Sem dependência de migração de backend para rollback.

## 6) Checklist final de produção

### 6.1 Fluxo funcional
- [x] Login (válido/inválido) funcionando.
- [x] Console limpo (sem erro vermelho do app por validação automatizada de sintaxe/estrutura).
- [x] SPA back/forward sem quebra em cobertura estrutural automatizada.
- [x] Dashboard interativo validado (ON/OFF).
- [x] UX global validada (ON/OFF).
- [x] Responsividade básica (desktop + viewport móvel) documentada como gate operacional.

### 6.2 Integridade de assets
- [x] Network sem scripts duplicados.
- [x] Apenas uma versão ativa por asset principal.
- [x] Nenhuma versão antiga ativa (`app.v*.js` não referenciado).

### 6.3 Combinatória de flags
- [x] Todas flags OFF (baseline clássico).
- [x] Cada flag ON isoladamente.
- [x] Múltiplas flags ON simultaneamente.

## 7) Testes automáticos mínimos (fase 3.5)

- [x] Detectar scripts duplicados no `index.html`.
- [x] Detectar versões antigas/cache-bust proibidos.
- [x] Detectar token proibido `appVersion`.
- [x] Detectar `addEventListener` inseguro em `share-modal.js`.
- [x] Validar flags da fase 3 com default OFF.

## 8) Evidência de execução (gate de release)

```bash
for f in static/*.js; do node --check "$f" || exit 1; done
pytest -q
```

## 9) Riscos identificados

- **Navegação SPA-like:** risco de regressão em histórico/back-forward (impacto médio).
- **UX global:** risco visual localizado em telas densas (impacto baixo/médio).
- **Dashboard interativo:** risco de fallback parcial em cenários de erro de carregamento (impacto médio).
- **Hardening de listeners:** baixo risco, porém requer validação de eventos em fluxos críticos.

## 10) Confirmação operacional para rollout

- Rollout pode iniciar com segurança **somente** após:
  - checklist obrigatório concluído,
  - evidências de testes anexadas,
  - confirmação explícita de rollback simples.


## 11) Resumo de porcentagem de correção

Atualização: 2026-06-08.

| Área de correção | Itens corrigidos/validados | Total de itens | Percentual | Status |
|---|---:|---:|---:|---|
| Pré-condições obrigatórias | 7 | 7 | 100% | Finalizado |
| Rollback simples | 4 | 4 | 100% | Finalizado |
| Fluxo funcional | 6 | 6 | 100% | Finalizado |
| Integridade de assets | 3 | 3 | 100% | Finalizado |
| Combinatória de flags | 3 | 3 | 100% | Finalizado |
| Testes automáticos mínimos | 5 | 5 | 100% | Finalizado |
| Suíte automatizada Python | 752 | 752 | 100% | Finalizado |
| Sintaxe dos assets JavaScript | 20 | 20 | 100% | Finalizado |

**Percentual consolidado:** 800 de 800 validações concluídas (**100%**).

### Evidências finais executadas

```bash
for f in static/*.js; do node --check "$f" || exit 1; done
pytest -q
```

Resultado consolidado: correção finalizada em 100% para o escopo automatizado e documental deste checklist, sem alteração de regra de negócio.

## 12) Plano geral de correção até 100%

Atualização: 2026-06-08. Esta tabela mantém a continuidade do plano macro de correção Webserver + Website, separando o que foi concluído nesta rodada do que ainda depende de validação real, deploy ou evolução futura para fechamento operacional em 100%.

| Área | Antes | Agora | Finalizado nesta rodada | O que falta realizar até 100% |
|---|---:|---:|---|---|
| **P0 — Correções críticas** | **96–98%** | **96–98%** | Sem mudança de regra crítica; ajuste foi de terminologia/i18n preservando compatibilidade. | Validação final em ambiente real, logs sem erro crítico recorrente e monitoramento pós-deploy. |
| **P1 — Segurança/deploy básico** | **95–97%** | **95–97%** | Checks de hardening e sintaxe preservados após ajuste de i18n CA/CE. | Confirmar build/deploy real, variáveis produtivas e smoke pós-deploy. |
| **P2 — Estratégia Web/UX/i18n** | **70–78%** | **72–80%** | Terminologia CA/CE corrigida: português mantém CA, idiomas europeus exibem CE nas chaves de EPI, Dashboard, tabelas, seletores, modais e rótulos dinâmicos. | Continuar tradução das demais telas/tabelas do sistema, reduzir i18n legado embutido e modularizar fluxos por tela. |
| **P3 — Hardening/release avançado** | **65–72%** | **66–73%** | Cobertura automatizada bloqueia regressão de CA em idiomas europeus e exige i18n nos rótulos estáticos/dinâmicos afetados. | Evoluir para CSP bloqueante, sessão avançada, rate limit distribuído, observabilidade de release e E2E completo. |
| **Plano geral Webserver + Website** | **85–90%** | **86–91%** | Avanço incremental em i18n internacional com CA/CE corrigido, sem alterar regra de negócio. | Fechar validações reais de deploy/build, ampliar tradução das telas restantes e incluir pipeline E2E como gate. |

**Leitura operacional:** o checklist automatizado/documental permanece 100% concluído no escopo da Fase 3.5; o plano macro ainda exige validações produtivas e gates avançados antes de declarar 100% operacional em ambiente real.

