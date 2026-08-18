# Configura o Runner.xcodeproj (gerado por `flutter create`) com os artefatos M1:
# - PRODUCT_BUNDLE_IDENTIFIER -> lido de Runner/Info.plist (fonte única)
# - CODE_SIGN_ENTITLEMENTS -> Runner/Runner.entitlements (push/APNs)
# - adiciona Runner/PrivacyInfo.xcprivacy ao "Copy Bundle Resources"
#
# Idempotente. Executar em macOS (gem `xcodeproj`). Não roda no Linux/backend.
require "xcodeproj"

ios_dir   = File.expand_path("..", __dir__)            # .../ios
proj_path = File.join(ios_dir, "Runner.xcodeproj")
plist_path = File.join(ios_dir, "Runner", "Info.plist")

unless File.exist?(proj_path)
  abort("[wire_xcode] #{proj_path} não existe. Rode `flutter create . --platforms=ios` antes.")
end

unless File.exist?(plist_path)
  abort("[wire_xcode] #{plist_path} não existe — ele é versionado e é a fonte do bundle id.")
end

project = Xcodeproj::Project.open(proj_path)
target  = project.targets.find { |t| t.name == "Runner" } or abort("[wire_xcode] target Runner não encontrado")

# 0) Bundle identifier — Info.plist é a ÚNICA fonte de verdade.
#
# `flutter create` deriva o PRODUCT_BUNDLE_IDENTIFIER de `--org` + nome do
# projeto, o que NÃO reproduz o identificador real do app (`epi_admin` ->
# `epiAdmin`, e não `epicontrole`). Como o Runner.xcodeproj não é versionado,
# sem este passo o projeto gerado nasceria com um identificador diferente do
# CFBundleIdentifier do app: o build `--no-codesign` passaria assim mesmo — ele
# não confere build setting contra provisioning — e a divergência só apareceria
# no build assinado, com o profile recusando o bundle id.
#
# Nada de identificador escrito aqui: cada repositório tem o seu no Info.plist
# (com.livamobile.* / com.rocksbrothers.*) e este script serve aos dois.
bundle_id = Xcodeproj::Plist.read_from_path(plist_path)["CFBundleIdentifier"].to_s.strip

if bundle_id.empty?
  abort("[wire_xcode] CFBundleIdentifier ausente ou vazio em #{plist_path}.")
end

# Um Info.plist com `$(PRODUCT_BUNDLE_IDENTIFIER)` (o padrão do template) faria
# a fonte apontar de volta para o destino — referência circular que se resolve
# em nada. Melhor abortar do que gravar um valor sem sentido.
if bundle_id.include?("$(")
  abort("[wire_xcode] CFBundleIdentifier é uma variável (#{bundle_id}). " \
        "O Info.plist precisa trazer o identificador literal para ser fonte de verdade.")
end

target.build_configurations.each do |config|
  config.build_settings["PRODUCT_BUNDLE_IDENTIFIER"] = bundle_id
end

# Alvos de teste herdam o identificador do app com o próprio nome como sufixo,
# que é a convenção do template (`<bundle id>.RunnerTests`).
project.targets.reject { |t| t == target }.each do |other|
  other.build_configurations.each do |config|
    config.build_settings["PRODUCT_BUNDLE_IDENTIFIER"] = "#{bundle_id}.#{other.name}"
  end
end

# 1) Entitlements em todas as configurações (Debug/Release/Profile)
target.build_configurations.each do |config|
  config.build_settings["CODE_SIGN_ENTITLEMENTS"] = "Runner/Runner.entitlements"
end

# 2) PrivacyInfo.xcprivacy como recurso do bundle
runner_group = project.main_group.find_subpath("Runner", true)
already = target.resources_build_phase.files.any? do |bf|
  bf.file_ref&.path&.end_with?("PrivacyInfo.xcprivacy")
end
unless already
  ref = runner_group.files.find { |f| f.path&.end_with?("PrivacyInfo.xcprivacy") }
  ref ||= runner_group.new_reference("PrivacyInfo.xcprivacy")
  target.resources_build_phase.add_file_reference(ref, true)
end

project.save
puts "[wire_xcode] OK: bundle id (#{bundle_id}) + entitlements + PrivacyInfo.xcprivacy configurados no Runner."
