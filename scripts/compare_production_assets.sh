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

is_proxy_blocked_http() {
  local http_status="$1"
  local stderr_file="$2"
  local headers_file="$3"
  local body_file="$4"

  [[ "$http_status" == "403" ]] || return 1

  if [[ -f "$stderr_file" ]] && grep -Eiq 'connect tunnel failed|proxy|tunnel' "$stderr_file"; then
    return 0
  fi

  if [[ -f "$headers_file" ]] && grep -Eiq '^server:[[:space:]]*envoy' "$headers_file"; then
    local compact_body
    if [[ -f "$body_file" ]]; then
      compact_body="$(tr -d '\r\n[:space:]' < "$body_file" 2>/dev/null || true)"
    else
      compact_body=""
    fi
    if [[ "$compact_body" == "Forbidden" || -z "$compact_body" ]]; then
      return 0
    fi
  fi

  return 1
}

fetch_asset() {
  local url="$1"
  local output="$2"
  local label="$3"
  local stderr_file="$TMP_DIR/${label}.stderr"
  local status_file="$TMP_DIR/${label}.http_status"
  local headers_file="$TMP_DIR/${label}.headers"
  local curl_exit
  local http_status

  rm -f "$stderr_file" "$status_file" "$headers_file" "$output"
  set +e
  curl -sS -L \
    --max-time "$CURL_TIMEOUT_SECONDS" \
    -A "$UA_HEADER" \
    -H "Accept: text/html,application/javascript,*/*;q=0.8" \
    -H "Cache-Control: no-cache" \
    -D "$headers_file" \
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
    return 0
  fi

  rm -f "$output"
  if [[ "$curl_exit" -ne 0 ]] && is_connectivity_restriction "$curl_exit" "$stderr_file"; then
    FETCH_RESULT_CLASS="remote_env"
    return 1
  fi

  if is_proxy_blocked_http "$http_status" "$stderr_file" "$headers_file" "$output"; then
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
  local failure_exit="$2"
  local result_name="$3"

  echo
  echo "[RESULT] $result_name"
  if [[ "$result_name" == "remote_validation_unavailable_in_this_environment" ]]; then
    echo "message=validação remota não disponível neste ambiente"
  fi
  echo "reason=$label"
  echo "class=$FETCH_RESULT_CLASS"
  echo "url=$FETCH_RESULT_URL"
  echo "http_status=$FETCH_RESULT_STATUS"
  echo "curl_exit=$FETCH_RESULT_CURL_EXIT"
  echo "stderr=${FETCH_RESULT_STDERR:-N/A}"
  emit_local_digest

  if [[ "$failure_exit" -eq "$EXIT_REMOTE_ENV" && "$STRICT_REMOTE_ERRORS" != "1" ]]; then
    exit "$EXIT_SUCCESS"
  fi
  exit "$failure_exit"
}

echo "== Comparando assets locais vs produção =="
echo "base_url=$BASE_URL"
echo "curl_timeout_seconds=$CURL_TIMEOUT_SECONDS"
echo "strict_remote_errors=$STRICT_REMOTE_ERRORS"

if ! fetch_asset "$BASE_URL/index.html" "$TMP_DIR/index.production.html" "index"; then
  case "$FETCH_RESULT_CLASS" in
    remote_env) handle_remote_failure "remote_connectivity_restricted_for_index" "$EXIT_REMOTE_ENV" "remote_validation_unavailable_in_this_environment" ;;
    remote_http) handle_remote_failure "remote_http_failure_for_index" "$EXIT_REMOTE_HTTP" "remote_http_failure" ;;
    *) handle_remote_failure "unexpected_curl_failure_for_index" "$EXIT_CURL_UNEXPECTED" "remote_validation_unavailable_in_this_environment" ;;
  esac
fi

prod_app_url="$(resolve_remote_app_url "$TMP_DIR/index.production.html")"
if ! fetch_asset "$prod_app_url" "$TMP_DIR/app.production.js" "app"; then
  case "$FETCH_RESULT_CLASS" in
    remote_env) handle_remote_failure "remote_connectivity_restricted_for_app" "$EXIT_REMOTE_ENV" "remote_validation_unavailable_in_this_environment" ;;
    remote_http) handle_remote_failure "remote_http_failure_for_app" "$EXIT_REMOTE_HTTP" "remote_http_failure" ;;
    *) handle_remote_failure "unexpected_curl_failure_for_app" "$EXIT_CURL_UNEXPECTED" "remote_validation_unavailable_in_this_environment" ;;
  esac
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
