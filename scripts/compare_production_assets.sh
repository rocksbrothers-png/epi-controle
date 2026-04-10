#!/usr/bin/env bash
set -euo pipefail
readonly EXIT_SUCCESS=0
readonly EXIT_USAGE=1
readonly EXIT_ASSET_DIFF=10
readonly EXIT_REMOTE_HTTP=20
readonly EXIT_REMOTE_ENV=30
readonly EXIT_CURL_UNEXPECTED=40

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <BASE_URL>"
  echo "Exemplo: $0 https://seu-app.onrender.com"
  exit "$EXIT_USAGE"
fi

readonly BASE_URL="${1%/}"
readonly LOCAL_INDEX="static/index.html"
readonly LOCAL_APP="static/app.js"
readonly UA_HEADER="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
readonly APP_QUERY_VERSION="${APP_QUERY_VERSION:-20260408-02}"
readonly CURL_TIMEOUT_SECONDS="${CURL_TIMEOUT_SECONDS:-15}"
readonly STRICT_REMOTE_ERRORS="${STRICT_REMOTE_ERRORS:-0}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

emit_local_digest() {
  local local_index_hash local_app_hash local_app_lines
  local_index_hash="$(sha256sum "$LOCAL_INDEX" | awk '{print $1}')"
  local_app_hash="$(sha256sum "$LOCAL_APP" | awk '{print $1}')"
  local_app_lines="$(wc -l < "$LOCAL_APP" | tr -d ' ')"

  echo "local.index.sha256=$local_index_hash"
  echo "local.app.sha256=$local_app_hash"
  echo "local.app.lines=$local_app_lines"
}

is_connectivity_restriction() {
  local curl_exit="$1"
  local stderr_file="$2"

  case "$curl_exit" in
    5|6|7|28|56) return 0 ;;
  esac

  if [[ -f "$stderr_file" ]] && grep -Eiq 'connect tunnel failed|proxy|could not resolve host|failed to connect|timed out|network is unreachable|connection reset' "$stderr_file"; then
    return 0
  fi

  return 1
}
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
  local label="$3"
  local stderr_file="$TMP_DIR/${label}.stderr"
  local status_file="$TMP_DIR/${label}.http_status"
  local curl_exit
  local http_status

  rm -f "$stderr_file" "$status_file" "$output"
  set +e
  curl -sS -L \
    --max-time "$CURL_TIMEOUT_SECONDS" \
  local status

  status="$(curl -sS -L \
    -A "$UA_HEADER" \
    -H "Accept: text/html,application/javascript,*/*;q=0.8" \
    -H "Cache-Control: no-cache" \
    -w '%{http_code}' \
    -o "$output" \
    "$url" >"$status_file" 2>"$stderr_file"
  curl_exit=$?
  set -e

  http_status="$(cat "$status_file" 2>/dev/null || echo "000")"
  FETCH_RESULT_URL="$url"
  FETCH_RESULT_STATUS="$http_status"
  FETCH_RESULT_CURL_EXIT="$curl_exit"
  FETCH_RESULT_STDERR="$(tr '\n' ' ' < "$stderr_file" 2>/dev/null | sed 's/[[:space:]]\+/ /g' | sed 's/^ //;s/ $//')"
  FETCH_RESULT_CLASS=""

  if [[ "$curl_exit" -eq 0 && "$http_status" =~ ^2[0-9][0-9]$ ]]; then
    FETCH_RESULT_CLASS="ok"
    "$url" || true)"

  if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
    return 0
  fi

  rm -f "$output"
  if [[ "$curl_exit" -ne 0 ]] && is_connectivity_restriction "$curl_exit" "$stderr_file"; then
    FETCH_RESULT_CLASS="remote_env"
    return 1
  fi

  if [[ "$http_status" == "403" ]]; then
    FETCH_RESULT_CLASS="remote_env"
    return 1
  fi

  if [[ "$http_status" =~ ^[0-9]{3}$ && ! "$http_status" =~ ^2[0-9][0-9]$ ]]; then
    FETCH_RESULT_CLASS="remote_http"
    return 1
  fi

  FETCH_RESULT_CLASS="curl_unexpected"
  return 1
}

resolve_remote_app_url() {
  local index_file="$1"
  local extracted_url

  extracted_url="$(sed -n 's/.*src="\([^"]*app[^"]*\.js[^"]*\)".*/\1/p' "$index_file" | head -n1)"
  if [[ -z "$extracted_url" ]]; then
    echo "$BASE_URL/app.js?v=$APP_QUERY_VERSION"
    return 0
  fi
  if [[ "$extracted_url" == http* ]]; then
    echo "$extracted_url"
    return 0
  fi
  echo "$BASE_URL/${extracted_url#/}"
}

handle_remote_failure() {
  local label="$1"
  local behavior_exit="$2"

  echo
  echo "[RESULT] skipped_due_to_remote_restriction"
  echo "reason=$label"
  echo "class=$FETCH_RESULT_CLASS"
  echo "url=$FETCH_RESULT_URL"
  echo "http_status=$FETCH_RESULT_STATUS"
  echo "curl_exit=$FETCH_RESULT_CURL_EXIT"
  echo "stderr=${FETCH_RESULT_STDERR:-N/A}"
  emit_local_digest

  if [[ "$STRICT_REMOTE_ERRORS" == "1" ]]; then
    exit "$behavior_exit"
  fi
  exit "$EXIT_SUCCESS"
}

echo "== Comparando assets locais vs produção =="
echo "base_url=$BASE_URL"
echo "curl_timeout_seconds=$CURL_TIMEOUT_SECONDS"
echo "strict_remote_errors=$STRICT_REMOTE_ERRORS"

if ! fetch_asset "$BASE_URL/index.html" "$TMP_DIR/index.production.html" "index"; then
  case "$FETCH_RESULT_CLASS" in
    remote_env) handle_remote_failure "remote_connectivity_restricted_for_index" "$EXIT_REMOTE_ENV" ;;
    remote_http) handle_remote_failure "remote_http_failure_for_index" "$EXIT_REMOTE_HTTP" ;;
    *) handle_remote_failure "unexpected_curl_failure_for_index" "$EXIT_CURL_UNEXPECTED" ;;
  esac
fi

prod_app_url="$(resolve_remote_app_url "$TMP_DIR/index.production.html")"
if ! fetch_asset "$prod_app_url" "$TMP_DIR/app.production.js" "app"; then
  case "$FETCH_RESULT_CLASS" in
    remote_env) handle_remote_failure "remote_connectivity_restricted_for_app" "$EXIT_REMOTE_ENV" ;;
    remote_http) handle_remote_failure "remote_http_failure_for_app" "$EXIT_REMOTE_HTTP" ;;
    *) handle_remote_failure "unexpected_curl_failure_for_app" "$EXIT_CURL_UNEXPECTED" ;;
  esac
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

echo "== Comparando assets locais vs produção =="
echo "Base URL: $BASE_URL"

curl -fsSL "$BASE_URL/index.html" -o "$TMP_DIR/index.production.html"
curl -fsSL "$BASE_URL/app.js?v=20260408-02" -o "$TMP_DIR/app.production.js"

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

index_status="equal"
app_status="equal"
if [[ "$local_index_hash" != "$prod_index_hash" ]]; then
  index_status="different"
fi
if [[ "$local_app_hash" != "$prod_app_hash" ]]; then
  app_status="different"
fi

echo
echo "index.local.sha256=$local_index_hash"
echo "index.remote.sha256=$prod_index_hash"
echo "index.comparison=$index_status"
echo "app.local.sha256=$local_app_hash"
echo "app.remote.sha256=$prod_app_hash"
echo "app.local.lines=$local_app_lines"
echo "app.remote.lines=$prod_app_lines"
echo "app.remote.url=$prod_app_url"
echo "app.comparison=$app_status"

if [[ "$index_status" == "equal" && "$app_status" == "equal" ]]; then
  echo "[RESULT] success_assets_match"
  exit "$EXIT_SUCCESS"
fi

echo "[RESULT] assets_diverge"
exit "$EXIT_ASSET_DIFF"

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
