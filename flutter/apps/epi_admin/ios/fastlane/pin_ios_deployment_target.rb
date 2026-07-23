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
# Idempotente: pode rodar mais de uma vez sem duplicar a linha `platform`
# nem empilhar blocos post_install repetidos.
#
# Uso: `ruby ios/fastlane/pin_ios_deployment_target.rb` a partir de
# flutter/apps/epi_admin, DEPOIS que o Podfile já existe (ex.: após
# `flutter build ios --config-only`).

IOS_DEPLOYMENT_TARGET = "15.5"
MARKER = "# pin_ios_deployment_target: managed block"

ios_dir = File.expand_path("..", __dir__) # .../ios
podfile_path = File.join(ios_dir, "Podfile")

unless File.exist?(podfile_path)
  abort("[pin_ios_deployment_target] #{podfile_path} não existe. Rode " \
        "`flutter build ios --config-only` antes.")
end

content = File.read(podfile_path)

# Remove qualquer post_install gerenciado por este script em execuções
# anteriores (sempre o último bloco do arquivo — ver append abaixo), para
# não empilhar blocos duplicados.
content = content.sub(/\n#{Regexp.escape(MARKER)}.*\z/m, "\n")

# Remove qualquer linha `platform :ios` pré-existente (comentada ou não) —
# vamos declarar a nossa, explícita, no topo.
lines = content.lines.reject { |l| l =~ /^\s*#?\s*platform\s+:ios\b/ }
content = lines.join

content = "platform :ios, '#{IOS_DEPLOYMENT_TARGET}'\n" + content

# CocoaPods executa múltiplos blocos `post_install` na ordem em que são
# registrados (não sobrescreve o hook padrão do Flutter) — seguro adicionar
# o nosso ao final, sem tocar no post_install gerado pelo `flutter create`.
content << <<~RUBY

  #{MARKER}
  post_install do |installer|
    installer.pods_project.targets.each do |target|
      target.build_configurations.each do |config|
        config.build_settings["IPHONEOS_DEPLOYMENT_TARGET"] = "#{IOS_DEPLOYMENT_TARGET}"
      end
    end
  end
RUBY

File.write(podfile_path, content)
puts "[pin_ios_deployment_target] platform :ios, '#{IOS_DEPLOYMENT_TARGET}' aplicado em #{podfile_path}"
