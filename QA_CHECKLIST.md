# QA Checklist Oficial — Front-end (Fase 3.5)

Este checklist padroniza a validação da estabilização final da UX moderna e a preparação para rollout controlado no projeto EPI.

## 1) Escopo e objetivo

- **Objetivo:** habilitar rollout gradual, seguro e reversível da UX moderna.
- **Escopo:** front-end (`static/`) e testes (`tests/`).
- **Fora de escopo:** backend, banco, permissões e regras de negócio.

## 2) Pré-condições obrigatórias (go/no-go)

- [ ] Erros de `ux-global.js` corrigidos.
- [ ] Erro `uxGlobalEnabled` corrigido.
- [ ] Console limpo.
- [ ] Login funcionando.
- [ ] Fases 3.1, 3.2, 3.3 e 3.4 concluídas.
- [ ] Scripts sem duplicidade.
- [ ] Cache-bust atualizado.

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

- [ ] Flag OFF restaura UX clássica.
- [ ] Limpar `localStorage` desativa UX moderna no navegador.
- [ ] Revert front-end é suficiente para retorno estável.
- [ ] Sem dependência de migração de backend para rollback.

## 6) Checklist final de produção

### 6.1 Fluxo funcional
- [ ] Login (válido/inválido) funcionando.
- [ ] Console limpo (sem erro vermelho do app).
- [ ] SPA back/forward sem quebra.
- [ ] Dashboard interativo validado (ON/OFF).
- [ ] UX global validada (ON/OFF).
- [ ] Responsividade básica (desktop + viewport móvel).

### 6.2 Integridade de assets
- [ ] Network sem scripts duplicados.
- [ ] Apenas uma versão ativa por asset principal.
- [ ] Nenhuma versão antiga ativa (`app.v*.js` não referenciado).

### 6.3 Combinatória de flags
- [ ] Todas flags OFF (baseline clássico).
- [ ] Cada flag ON isoladamente.
- [ ] Múltiplas flags ON simultaneamente.

## 7) Testes automáticos mínimos (fase 3.5)

- [ ] Detectar scripts duplicados no `index.html`.
- [ ] Detectar versões antigas/cache-bust proibidos.
- [ ] Detectar token proibido `appVersion`.
- [ ] Detectar `addEventListener` inseguro em `share-modal.js`.
- [ ] Validar flags da fase 3 com default OFF.

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
