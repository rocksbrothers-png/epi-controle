# Fase 5.0 — Ativação Controlada (Go Live Progressivo)

Data: 2026-04-24.

## 1) Matriz final de ativação

| Fase | Flag (querystring) | Status | Pronto para produção | Risco | Pode ativar? |
|---|---|---|---|---|---|
| 4.1 | `ux_phase41_enabled` (`ux_phase41=1`) | OK | SIM | baixo | SIM |
| 4.2 | `ux_phase42_enabled` (`ux_phase42=1`) | OK | SIM | médio | SIM (controlado) |
| 4.3 | `ux_phase43_enabled` (`ux_phase43=1`) | OK | SIM | médio | SIM (controlado) |
| 4.4 | `ux_phase44_enabled` (`ux_phase44=1`) | OK | SIM | baixo | SIM |
| Hierarchy | `ux_hierarchical_navigation_enabled` (`ux_hierarchy=1`) | OK | SIM | baixo | SIM |
| SPA | `spa_navigation_enabled` (`ux_spa_navigation=1`) | OK | SIM | baixo | SIM |
| Tabs | `ux_multitab_navigation_enabled` (`ux_multitab=1`) | OK | SIM | médio | faseada |

## 2) Estratégia de rollout progressivo

### Fase 1 (interna)
- Ativar apenas via querystring para usuários-chave.
- Confirmar login, troca de telas, e console limpo.

### Fase 2 (teste real)
- Ativar manualmente via `localStorage` para piloto restrito.
- Exemplo:
  - `localStorage.setItem('ux_phase44_enabled', '1')`
  - `localStorage.setItem('ux_multitab_navigation_enabled', '1')`

### Fase 3 (parcial)
- Ativar para grupos controlados por perfil/time de operação.
- Coletar snapshot de monitoramento por tela e por API.

### Fase 4 (produção total)
- Somente após janela estável (sem erro crítico regressivo).
- Considerar `default ON` em janela planejada com rollback pronto.

## 3) Controle central de flags

- Resolver único: `getFeatureFlagResolution`.
- Precedência: **querystring > localStorage > default**.
- Exposição central segura: `window.__EPI_FEATURE_FLAGS__` (somente leitura).

## 4) Monitoramento operacional

`error-monitor.js` passa a expor `window.__EPI_MONITORING__.getSnapshot()` com:
- `errorsByModule` (contador por tela/módulo ativo);
- `unstableApis` (contador por endpoint/status);
- `criticalFailures` (buffer circular de falhas críticas).

## 5) Fallback obrigatório

Se houver instabilidade:
1. Remover querystring de ativação.
2. Zerar flags de piloto no `localStorage`.
3. Hard refresh.
4. Confirmar login e navegação no modo clássico (flags OFF).

## 6) Evidência objetiva desta rodada

- Sintaxe JavaScript validada.
- Suíte `pytest` completa aprovada.
- Nenhuma flag alterada para default ON.
- Sem criação de nova feature funcional de negócio.

## 7) Riscos remanescentes

1. Regressão combinatória em uso simultâneo de SPA + Hierarchy + Tabs.
2. Necessidade de validação manual final de console em browser real com extensões desabilitadas.
3. Dependência de disciplina operacional para desligamento rápido por flag em incidente.

## 8) Recomendação

**Pronto para ativação controlada da Fase 5.0.**

**Não recomendado ativar default ON imediatamente.**
Prosseguir com rollout faseado e gate de estabilidade (console limpo + navegação + operações críticas).

## 9) Fase 5.0-A — Hardening final aplicado

### Riscos eliminados
- Interceptação duplicada/agressiva de `fetch`.
- Crescimento não controlado de buffers de monitoramento.
- Mutação externa da API central de flags e monitoramento.
- Permanência da UX moderna durante incidente crítico.

### Limites definidos
- `errorsByModule`: máximo 50 eventos por módulo.
- `unstableApis`: máximo 50 endpoints monitorados.
- `criticalFailures`: buffer FIFO máximo 100 eventos.

### Salvaguardas automáticas
- Kill switch mestre: `ux_global_kill_switch` (`ux_kill_switch=1`) força UX em modo clássico.
- Rollback automático para modo clássico quando:
  - mais de 10 erros em janela de 10s; ou
  - mais de 5 respostas 5xx consecutivas.

### Status final
**Sistema pronto para rollout controlado seguro**, mantendo default OFF e rollback imediato por flag.
