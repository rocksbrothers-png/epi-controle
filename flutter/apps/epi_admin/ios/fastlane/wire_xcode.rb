# Configura o Runner.xcodeproj (gerado por `flutter create`) com os artefatos M1:
# - CODE_SIGN_ENTITLEMENTS -> Runner/Runner.entitlements (push/APNs)
# - adiciona Runner/PrivacyInfo.xcprivacy ao "Copy Bundle Resources"
#
# Idempotente. Executar em macOS (gem `xcodeproj`). Não roda no Linux/backend.
require "xcodeproj"

ios_dir   = File.expand_path("..", __dir__)            # .../ios
proj_path = File.join(ios_dir, "Runner.xcodeproj")

unless File.exist?(proj_path)
  abort("[wire_xcode] #{proj_path} não existe. Rode `flutter create . --platforms=ios` antes.")
end

project = Xcodeproj::Project.open(proj_path)
target  = project.targets.find { |t| t.name == "Runner" } or abort("[wire_xcode] target Runner não encontrado")

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
puts "[wire_xcode] OK: entitlements + PrivacyInfo.xcprivacy configurados no Runner."
