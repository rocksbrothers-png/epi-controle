# Confere que o Runner.xcodeproj GERADO carrega o mesmo bundle identifier que o
# Runner/Info.plist versionado.
#
# Por que existe: o build `--no-codesign` do CI não é capaz de pegar essa
# divergência. O CFBundleIdentifier do app vem do Info.plist processado, então
# um PRODUCT_BUNDLE_IDENTIFIER errado no projeto passa despercebido e só falha
# no build assinado, contra o provisioning profile — que roda apenas em tag
# `vX.Y.Z`. Esta verificação traz o defeito para o CI de todo push/PR.
#
# Por que NÃO reusa o `wire_xcode.rb`: uma guarda que compartilha o mecanismo
# do código que ela verifica compartilha também os defeitos dele. Aqui os dois
# arquivos são lidos como TEXTO, sem a gem `xcodeproj` e sem o parser de plist
# usados na gravação — se aquele caminho quebrar, este acusa.
#
# Uso: `ruby ios/fastlane/verify_bundle_id.rb` a partir de flutter/apps/epi_admin,
# DEPOIS de `flutter create` + `wire_xcode.rb`.

ios_dir    = File.expand_path("..", __dir__) # .../ios
plist_path = File.join(ios_dir, "Runner", "Info.plist")
pbxproj    = File.join(ios_dir, "Runner.xcodeproj", "project.pbxproj")

abort("[verify_bundle_id] #{plist_path} não existe.") unless File.exist?(plist_path)
unless File.exist?(pbxproj)
  abort("[verify_bundle_id] #{pbxproj} não existe — a geração do projeto iOS falhou.")
end

# ── Info.plist, lido como texto ───────────────────────────────────────────
# `encoding:` explícito: o Info.plist tem acentos (descrições de permissão em
# português) e `File.read` usa o encoding externo padrão do ambiente. Onde ele
# não é UTF-8, a leitura estoura em `invalid byte sequence` no primeiro regex —
# e o script falharia por motivo errado, inclusive no caso correto.
plist = File.read(plist_path, encoding: "UTF-8")
match = plist[%r{<key>\s*CFBundleIdentifier\s*</key>\s*<string>([^<]*)</string>}m, 1]
esperado = match.to_s.strip

if esperado.empty?
  abort("[verify_bundle_id] CFBundleIdentifier ausente ou vazio em #{plist_path}.")
end

# ── project.pbxproj, lido como texto ──────────────────────────────────────
encontrados = File.read(pbxproj, encoding: "UTF-8").scan(/PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^";\n]+)"?\s*;/).flatten.map(&:strip).uniq

if encontrados.empty?
  abort("[verify_bundle_id] nenhum PRODUCT_BUNDLE_IDENTIFIER em #{pbxproj} — " \
        "o `wire_xcode.rb` não rodou ou não gravou nada.")
end

# O alvo do app usa o identificador exato; alvos de teste usam sufixo
# (`<bundle id>.RunnerTests`). Qualquer outra coisa é divergência.
divergentes = encontrados.reject { |id| id == esperado || id.start_with?("#{esperado}.") }

unless divergentes.empty?
  warn "[verify_bundle_id] ERRO: bundle id divergente entre Info.plist e o projeto gerado."
  warn "  Info.plist (fonte):     #{esperado}"
  warn "  project.pbxproj:        #{encontrados.join(', ')}"
  warn "  não conferem:           #{divergentes.join(', ')}"
  warn "  O build assinado falharia contra o provisioning profile."
  abort
end

unless encontrados.include?(esperado)
  warn "[verify_bundle_id] ERRO: nenhum target usa o identificador do app."
  warn "  Info.plist (fonte):  #{esperado}"
  warn "  project.pbxproj:     #{encontrados.join(', ')}"
  abort
end

puts "[verify_bundle_id] OK: #{esperado} (#{encontrados.size} valor(es) no projeto: #{encontrados.join(', ')})"
