#!/usr/bin/env bash
#
# Gate de i18n: bloqueia strings hardcoded novas voltadas ao usuário dentro de
# lib/features. Cobre os padrões mais comuns de vazamento de texto fixo:
#
#   • Text('Salvar')
#   • label:      'Próximo'      (EpiButton, etc.)
#   • labelText:  'Quantidade'   (InputDecoration)
#   • hintText:   'Buscar...'    (InputDecoration)
#   • helperText: '...'
#   • tooltip:    '...'
#   • SnackBar(content: Text('...'))   — coberto pelo padrão Text('...')
#
# Strings de débito pré-existente OU exceções legítimas (ex.: autônimos de
# idioma na tela de Configurações) ficam registradas na allowlist
# (tool/i18n_hardcoded_allowlist.txt). Qualquer ocorrência fora da allowlist
# faz o gate falhar — forçando o uso de AppLocalizations (epi_i18n).
#
# Uso: rodar a partir de flutter/ (working-directory do CI).
set -euo pipefail

APP_DIR="apps/epi_admin"
ALLOWLIST="tool/i18n_hardcoded_allowlist.txt"

cd "$(dirname "$0")/.."

SCAN="$APP_DIR/lib/features"

# A varredura vive em tool/i18n_scan.py. Ela já foi feita aqui com dois
# `grep -rnoE`, e cada um escondia um defeito que só apareceu quando o gate foi
# auditado: a classe `[A-Za-zÀ-ÿ]` abortava sob C.UTF-8 (o locale dos runners)
# e o `|| true` transformava o erro em lista vazia — verde sem ter varrido
# nada; e `grep`, sendo orientado a linha, nunca via um `Text(` quebrado em
# várias linhas. Ver o cabeçalho do i18n_scan.py.
#
# Sem `|| true`: se a varredura falhar, o gate falha. Passar sem ter procurado
# é o pior resultado possível para um gate.
current="$(python3 tool/i18n_scan.py "$APP_DIR" "$SCAN" | sort -u)"


# Allowlist (ignora comentários e linhas em branco).
allow="$(grep -vE '^\s*(#|$)' "$ALLOWLIST" | sort -u || true)"

# Diferença: o que está no código mas não na allowlist.
violations="$(comm -23 <(printf '%s\n' "$current") <(printf '%s\n' "$allow") || true)"

if [[ -n "${violations//[$'\n\t ']/}" ]]; then
  echo "❌ Strings hardcoded novas detectadas (use AppLocalizations / epi_i18n):"
  echo "$violations" | sed 's/^/   • /'
  echo
  echo "Se for débito legítimo ou exceção intencional, adicione a linha em $ALLOWLIST"
  echo "com um comentário explicando o porquê."
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
