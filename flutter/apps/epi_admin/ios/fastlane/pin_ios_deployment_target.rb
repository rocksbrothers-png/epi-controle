# Fixa o deployment target mínimo do iOS no Podfile gerado pelo Flutter.
#
# O Podfile NÃO é versionado (gerado do zero por `flutter build ios
# --config-only`, ver ios_ci.yml / deploy-ios.yml). Plugins como
# google_mlkit_commons passaram a exigir iOS >= 15.5; sem uma linha
# `platform :ios` explícita, o CocoaPods assume 13.0 e a resolução falha:
#
#   [!] CocoaPods could not find compatible versions for pod
#   "google_mlkit_commons": ... required a higher minimum deployment target.
#   Error: ... increase your application's deployment target to at least 15.5
#
# Só declaramos `platform :ios, 'X'` — não adicionamos um post_install
# próprio: o CocoaPods 1.17 rejeita blocos post_install duplicados
# ("Specifying multiple `post_install` hooks is unsupported"), e o
# Podfile gerado pelo Flutter já vem com o seu próprio post_install
# padrão. Declarar `platform :ios` já é suficiente para a resolução de
# dependências (é exatamente o valor que o CocoaPods compara contra o
# deployment target mínimo exigido pelos pods) e o CocoaPods já aplica
# esse mínimo como IPHONEOS_DEPLOYMENT_TARGET para todos os pod targets
# por padrão.
#
# Idempotente: pode rodar mais de uma vez sem duplicar a linha `platform`.
#
# Uso: `ruby ios/fastlane/pin_ios_deployment_target.rb` a partir de
# flutter/apps/epi_admin, DEPOIS que o Podfile já existe (ex.: após
# `flutter build ios --config-only`).

IOS_DEPLOYMENT_TARGET = "15.5"

ios_dir = File.expand_path("..", __dir__) # .../ios
podfile_path = File.join(ios_dir, "Podfile")

unless File.exist?(podfile_path)
  abort("[pin_ios_deployment_target] #{podfile_path} não existe. Rode " \
        "`flutter build ios --config-only` antes.")
end

content = File.read(podfile_path)

# Remove qualquer linha `platform :ios` pré-existente (comentada ou não) —
# vamos declarar a nossa, explícita, no topo.
lines = content.lines.reject { |l| l =~ /^\s*#?\s*platform\s+:ios\b/ }
content = lines.join

content = "platform :ios, '#{IOS_DEPLOYMENT_TARGET}'\n" + content

File.write(podfile_path, content)
puts "[pin_ios_deployment_target] platform :ios, '#{IOS_DEPLOYMENT_TARGET}' aplicado em #{podfile_path}"
