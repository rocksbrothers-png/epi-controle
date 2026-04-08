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

echo "== Comparando assets locais vs produção =="
echo "Base URL: $BASE_URL"

curl -fsSL "$BASE_URL/index.html" -o "$TMP_DIR/index.production.html"
curl -fsSL "$BASE_URL/app.js?v=20260408-02" -o "$TMP_DIR/app.production.js"

LOCAL_INDEX="static/index.html"
LOCAL_APP="static/app.js"

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
