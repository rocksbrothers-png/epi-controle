# QA Checklist Oficial — Front-end (Fase 3.4)

Este checklist padroniza a validação de front-end antes de cada deploy da aplicação EPI.

## 1) Escopo e objetivo

- **Objetivo:** reduzir regressões no rollout da UX moderna com rollback simples.
- **Escopo:** front-end (`static/`) e testes (`tests/`).
- **Fora de escopo:** backend, banco, permissões e regras de negócio.

## 2) Matriz de flags (Fase 3)

| Flag | Querystring | Tela/Módulo | Default | Status |
|---|---|---|---|---|
| `dashboard_interativo_enabled` | `ux_dashboard_interativo` | Dashboard interativo | OFF | Pilot estável |
| `spa_navigation_enabled` | `ux_spa_navigation` | Navegação SPA-like (menu + histórico) | OFF | Pilot controlado |
| `ux_global_enabled` | `ux_global` | UX global (componentes/context bars/estilos fase 3) | OFF | Pilot estável |
| `ux_performance_hardening_enabled` | `ux_perf_hardening` | Hardening de listeners/segurança de binding | OFF | Pilot controlado |

## 3) Checklist obrigatório por deploy

### 3.1 Fluxos funcionais
- [ ] Login (usuário válido e inválido) funcionando.
- [ ] Console limpo (sem erro vermelho do app).
- [ ] Navegação principal funcionando entre telas críticas.
- [ ] Back/forward sem quebra de estado crítico.
- [ ] Responsividade básica (desktop + viewport móvel).

### 3.2 Integridade de assets
- [ ] Sem scripts duplicados no `index.html`.
- [ ] Apenas uma versão ativa de cada asset principal.
- [ ] Nenhum cache-bust antigo ativo.

### 3.3 Validação de feature flags
- [ ] Flags OFF preservam UX clássica.
- [ ] Flags ON habilitam apenas módulos esperados.
- [ ] Combinação de múltiplas flags ON sem erro de console.
- [ ] Defaults permanecem OFF no código.

### 3.4 Segurança/hardening front-end
- [ ] Sem token global proibido (`appVersion`).
- [ ] `share-modal.js` sem `addEventListener` inseguro em alvo nulo.
- [ ] `node --check` em todos os JS sem erro de sintaxe.

## 4) Procedimento de ativação controlada

1. **Etapa 1 — Querystring (admin/teste):** ativar por URL para validação pontual.
2. **Etapa 2 — Validação por tela:** executar fluxo mínimo por módulo afetado.
3. **Etapa 3 — Storage controlado:** habilitar por storage para grupo piloto.
4. **Etapa 4 — Avaliação de default ON:** só após ciclo completo sem regressão.

## 5) Checklist de rollback

- [ ] Desativar a flag problemática (query/storage).
- [ ] Limpar `localStorage` do ambiente de teste/piloto.
- [ ] Reverter commit front-end se necessário.
- [ ] Validar retorno ao fluxo clássico (login + navegação + telas críticas).
- [ ] Confirmar console limpo após rollback.

## 6) Comandos de evidência (gate de release)

```bash
for f in static/*.js; do node --check "$f" || exit 1; done
pytest -q
```

## 7) Validação manual de browser (produção/pós-deploy)

1. Abrir aba anônima.
2. DevTools → Network → **Disable cache**.
3. Recarregar com `Ctrl+F5`.
4. Confirmar apenas uma versão ativa de cada asset principal.
5. Confirmar console limpo.
6. Confirmar login e navegação básica.
