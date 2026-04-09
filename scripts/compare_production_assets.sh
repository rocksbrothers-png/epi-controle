#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <BASE_URL>"
  echo "Exemplo: $0 https://seu-app.onrender.com"
  exit 1
fi

BASE_URL="${1%/}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
UA_HEADER="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
APP_QUERY_VERSION="${APP_QUERY_VERSION:-20260408-02}"

fetch_asset() {
  local url="$1"
  local output="$2"
  local status

  status="$(curl -sS -L \
    -A "$UA_HEADER" \
    -H "Accept: text/html,application/javascript,*/*;q=0.8" \
    -H "Cache-Control: no-cache" \
    -w '%{http_code}' \
    -o "$output" \
    "$url" || true)"

  if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
    return 0
  fi

  rm -f "$output"
  echo "[ERRO] Falha ao baixar $url (HTTP $status)." >&2
  return 1
}

echo "== Comparando assets locais vs produção =="
echo "Base URL: $BASE_URL"
echo "User-Agent: $UA_HEADER"

if ! fetch_asset "$BASE_URL/index.html" "$TMP_DIR/index.production.html"; then
  echo "[DICA] O host pode estar bloqueando requisições sem sessão/cookies."
  echo "       Tente rodar localmente: APP_QUERY_VERSION=$APP_QUERY_VERSION $0 \"$BASE_URL\""
  exit 2
fi

LOCAL_INDEX="static/index.html"
LOCAL_APP="static/app.js"

prod_app_url=""
if command -v sed >/dev/null 2>&1; then
  prod_app_url="$(sed -n 's/.*src="\([^"]*app[^"]*\.js[^"]*\)".*/\1/p' "$TMP_DIR/index.production.html" | head -n1)"
fi

if [[ -z "$prod_app_url" ]]; then
  prod_app_url="/app.js?v=$APP_QUERY_VERSION"
elif [[ "$prod_app_url" != http* ]]; then
  prod_app_url="$BASE_URL/${prod_app_url#/}"
fi

if ! fetch_asset "$prod_app_url" "$TMP_DIR/app.production.js"; then
  if ! fetch_asset "$BASE_URL/app.js?v=$APP_QUERY_VERSION" "$TMP_DIR/app.production.js"; then
    echo "[ERRO] Não foi possível baixar app.js em produção."
    echo "       URL tentada no index: ${prod_app_url:-N/A}"
    echo "       Fallback: $BASE_URL/app.js?v=$APP_QUERY_VERSION"
    exit 3
  fi
fi

local_index_hash="$(sha256sum "$LOCAL_INDEX" | awk '{print $1}')"
prod_index_hash="$(sha256sum "$TMP_DIR/index.production.html" | awk '{print $1}')"
local_app_hash="$(sha256sum "$LOCAL_APP" | awk '{print $1}')"
prod_app_hash="$(sha256sum "$TMP_DIR/app.production.js" | awk '{print $1}')"

local_app_lines="$(wc -l < "$LOCAL_APP" | tr -d ' ')"
prod_app_lines="$(wc -l < "$TMP_DIR/app.production.js" | tr -d ' ')"

echo
echo "index.html  local: $local_index_hash"
echo "index.html  prod : $prod_index_hash"
echo "app.js      local: $local_app_hash (linhas: $local_app_lines)"
echo "app.js      prod : $prod_app_hash (linhas: $prod_app_lines)"
echo "app.js      prod URL: $prod_app_url"

echo
if [[ "$local_index_hash" == "$prod_index_hash" ]]; then
  echo "[OK] index.html em produção é idêntico ao repositório."
else
  echo "[ALERTA] index.html em produção difere do repositório."
fi

if [[ "$local_app_hash" == "$prod_app_hash" ]]; then
  echo "[OK] app.js em produção é idêntico ao repositório."
else
  echo "[ALERTA] app.js em produção difere do repositório."
fi

if [[ "$prod_app_lines" -lt "$local_app_lines" ]]; then
  echo "[ALERTA] app.js em produção possui menos linhas (possível truncamento)."
fi
