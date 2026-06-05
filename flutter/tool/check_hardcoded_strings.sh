#!/usr/bin/env bash
#
# Gate de i18n: bloqueia strings hardcoded novas em widgets Text(...) dentro de
# lib/features. Strings de débito pré-existente ficam registradas na allowlist
# (tool/i18n_hardcoded_allowlist.txt). Qualquer ocorrência fora da allowlist
# faz o gate falhar — forçando o uso de AppLocalizations (epi_i18n).
#
# Uso: rodar a partir de flutter/ (working-directory do CI).
set -euo pipefail

APP_DIR="apps/epi_admin"
ALLOWLIST="tool/i18n_hardcoded_allowlist.txt"

cd "$(dirname "$0")/.."

# Coleta ocorrências atuais no formato arquivo|texto (sem nº de linha).
current="$(grep -rnoE "Text\(\s*'[^'\$]*[A-Za-zÀ-ÿ][^'\$]*'" "$APP_DIR/lib/features" 2>/dev/null \
  | sed -E "s#^$APP_DIR/([^:]+):[0-9]+:Text\(\s*'(.*)'#\1|\2#" \
  | sort -u || true)"

# Allowlist (ignora comentários e linhas em branco).
allow="$(grep -vE '^\s*(#|$)' "$ALLOWLIST" | sort -u || true)"

# Diferença: o que está no código mas não na allowlist.
violations="$(comm -23 <(printf '%s\n' "$current") <(printf '%s\n' "$allow") || true)"

if [[ -n "${violations//[$'\n\t ']/}" ]]; then
  echo "❌ Strings hardcoded novas detectadas (use AppLocalizations / epi_i18n):"
  echo "$violations" | sed 's/^/   • /'
  echo
  echo "Se for débito legítimo e intencional, adicione a linha em $ALLOWLIST."
  exit 1
fi

# Avisa sobre entradas obsoletas na allowlist (já corrigidas) — não bloqueia.
stale="$(comm -13 <(printf '%s\n' "$current") <(printf '%s\n' "$allow") || true)"
if [[ -n "${stale//[$'\n\t ']/}" ]]; then
  echo "ℹ️  Entradas obsoletas na allowlist (string já removida do código):"
  echo "$stale" | sed 's/^/   • /'
  echo "   Considere removê-las de $ALLOWLIST."
fi

echo "✅ Sem strings hardcoded novas."
