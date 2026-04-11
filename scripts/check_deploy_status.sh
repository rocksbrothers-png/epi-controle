#!/usr/bin/env bash
set -euo pipefail

echo "== Verificação de GitHub e Render =="

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'desconhecida')"
last_commit="$(git log -1 --pretty=format:'%h - %s (%ci)' 2>/dev/null || echo 'sem commits')"

echo "Branch atual: $branch"
echo "Último commit: $last_commit"

echo
if git remote get-url origin >/dev/null 2>&1; then
  origin_url="$(git remote get-url origin)"
  echo "[OK] Remote origin configurado: $origin_url"
else
  echo "[ERRO] Remote origin NÃO está configurado."
  echo "       Sem origin, os commits locais não chegam ao GitHub."
fi

echo
if [[ -f "render.yaml" ]]; then
  echo "[OK] render.yaml encontrado (Blueprint do Render)."
else
  echo "[ALERTA] render.yaml não encontrado neste repositório."
  echo "         O deploy no Render pode estar configurado manualmente no dashboard."
fi

echo
if [[ -n "${RENDER_API_KEY:-}" ]]; then
  echo "[INFO] RENDER_API_KEY detectada no ambiente."
else
  echo "[INFO] RENDER_API_KEY não detectada no ambiente local."
fi

echo
if git status --porcelain | grep -q .; then
  echo "[INFO] Existem alterrazão não commitadas localmente."
else
  echo "[OK] Working tree limpo."
fi

echo
cat <<'MSG'
Próximos passos recomendados:
1) Configurar remote origin para o GitHub.
2) Fazer push da branch para o GitHub.
3) No Render, confirmar que o serviço está conectado ao mesmo repositório/branch.
4) Verificar logs de deploy no painel do Render após o push.
MSG
