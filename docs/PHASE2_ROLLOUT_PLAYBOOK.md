# EPI Controle — Phase 2.8 Rollout Gradual (Front-end)

Data de referência: **2026-04-24**.

## 1) Padrão de ativação gradual por módulo

### Regras
- Todos os módulos Phase 2 ficam **OFF por padrão**.
- Ativação preferencial por **querystring** (sessão atual).
- Ativação por **localStorage** só é considerada quando o controle de rollout de storage estiver ligado:
  - `?ux_phase2_storage=1`, ou
  - `localStorage["epi_phase2_rollout_storage_enabled"] = "1"`.
- Sem backend nesta fase: estratégia é totalmente client-side.

### Sequência operacional recomendada
1. Habilitar 1 módulo por vez via querystring.
2. Validar login, console e navegação.
3. Testar combinação de 2 módulos.
4. Se estável, opcionalmente persistir em localStorage para o operador responsável.

---

## 2) Matriz de flags Phase 2

| Flag | Querystring | Módulo / Tela | Default | Status atual |
|---|---|---|---|---|
| `colaborador_htmx_enabled` | `ux_phase2_colaboradores` | Cadastro de Colaborador | OFF | Pilot estável |
| `colaborador_list_htmx_enabled` | `ux_phase2_colab_list` | Listagem de Colaboradores | OFF | Pilot estável |
| `gestao_colaborador_htmx_enabled` | `ux_phase2_gestao_colab` | Gestão de Colaborador | OFF | Pilot estável |
| `epi_htmx_enabled` | `ux_phase2_epis` | Cadastro de EPI | OFF | Pilot estável |
| `estoque_htmx_enabled` | `ux_phase2_estoque` | Controle de Estoque (somente leitura + filtros) | OFF | Pilot controlado |

---

## 3) Procedimento de rollout (produção)

### 3.1 Ativação pontual (sem persistência)
Exemplo:
```text
https://<host>/?ux_phase2_estoque=1
```

### 3.2 Ativação com persistência local (controlada)
1. Abrir com `?ux_phase2_storage=1` (habilita uso de storage para flags).
2. Definir a flag desejada no console:
```js
localStorage.setItem("estoque_htmx_enabled", "1");
```
3. Recarregar a tela.

> Observação: manter o uso de storage restrito a usuários técnicos/QA durante o piloto.

---

## 4) Procedimento de rollback

1. **Desativar querystring** removendo `ux_phase2_*` da URL.
2. Se houver persistência local, limpar:
```js
localStorage.removeItem("estoque_htmx_enabled");
localStorage.removeItem("epi_phase2_rollout_storage_enabled");
```
3. Hard refresh (`Ctrl+F5`).
4. Confirmar fluxo clássico da tela.
5. Se necessário, rollback de código front-end (reverter commit).

---

## 5) Checklist de validação em produção

- [ ] Login funcionando.
- [ ] Console limpo (sem erro vermelho).
- [ ] Navegação entre telas sem quebra.
- [ ] Flag OFF mantém fluxo clássico.
- [ ] Flag ON ativa apenas módulo esperado.
- [ ] Múltiplas flags ON sem conflito.
- [ ] Sem duplicação de listeners/rebind em navegação repetida.

### Cenários mínimos
1. `?ux_phase2_estoque=1`
2. `?ux_phase2_colab_list=1`
3. `?ux_phase2_estoque=1&ux_phase2_colab_list=1`

---

## 6) Riscos identificados

- **Risco de configuração local**: uso indevido de localStorage pode manter piloto ativo além do esperado.
- **Risco de regressão visual**: toolbar/status HTMX pode divergir do fluxo clássico em telas com alto uso.
- **Mitigação**: rollout por módulo, validação de console e rollback imediato por URL/localStorage.
