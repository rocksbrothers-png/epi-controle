/// Perfil da própria empresa (Configurações > Minha Empresa).
///
/// Espelha `GET/PUT /api/my-company`: o Administrador Geral (Owner da tenant)
/// edita dados cadastrais, identidade visual, tema, domínio e preferências.
/// Campos estruturais (plano, limites, licença) são somente leitura — o
/// backend ignora qualquer tentativa de gravação fora do whitelist.
class MyCompanyProfile {
  const MyCompanyProfile({
    required this.id,
    required this.name,
    this.legalName = '',
    this.cnpj = '',
    this.stateRegistration = '',
    this.municipalRegistration = '',
    this.address = '',
    this.contactPhone = '',
    this.whatsapp = '',
    this.contactEmail = '',
    this.website = '',
    this.displayName = '',
    this.institutionalMessage = '',
    this.primaryColor = '',
    this.secondaryColor = '',
    this.accentColor = '',
    this.themeJson = '',
    this.slug = '',
    this.subdomain = '',
    this.customDomain = '',
    this.defaultLanguage = '',
    this.timezone = '',
    this.planName = '',
    this.userLimit = 0,
    this.licenseStatus = '',
    this.onboardingCompleted = true,
  });

  final int id;
  final String name;
  final String legalName;
  final String cnpj;
  final String stateRegistration;
  final String municipalRegistration;
  final String address;
  final String contactPhone;
  final String whatsapp;
  final String contactEmail;
  final String website;
  final String displayName;
  final String institutionalMessage;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final String themeJson;
  final String slug;
  final String subdomain;
  final String customDomain;
  final String defaultLanguage;
  final String timezone;

  // Somente leitura (contrato — administrado pelo Master)
  final String planName;
  final int userLimit;
  final String licenseStatus;
  final bool onboardingCompleted;

  static String _s(Map<String, dynamic> json, String key) =>
      (json[key] as String?) ?? '';

  factory MyCompanyProfile.fromJson(Map<String, dynamic> json) =>
      MyCompanyProfile(
        id: (json['id'] as num?)?.toInt() ?? 0,
        name: _s(json, 'name'),
        legalName: _s(json, 'legal_name'),
        cnpj: _s(json, 'cnpj'),
        stateRegistration: _s(json, 'state_registration'),
        municipalRegistration: _s(json, 'municipal_registration'),
        address: _s(json, 'address'),
        contactPhone: _s(json, 'contact_phone'),
        whatsapp: _s(json, 'whatsapp'),
        contactEmail: _s(json, 'contact_email'),
        website: _s(json, 'website'),
        displayName: _s(json, 'display_name'),
        institutionalMessage: _s(json, 'institutional_message'),
        primaryColor: _s(json, 'primary_color'),
        secondaryColor: _s(json, 'secondary_color'),
        accentColor: _s(json, 'accent_color'),
        themeJson: _s(json, 'theme_json'),
        slug: _s(json, 'slug'),
        subdomain: _s(json, 'subdomain'),
        customDomain: _s(json, 'custom_domain'),
        defaultLanguage: _s(json, 'default_language'),
        timezone: _s(json, 'timezone'),
        planName: _s(json, 'plan_name'),
        userLimit: (json['user_limit'] as num?)?.toInt() ?? 0,
        licenseStatus: _s(json, 'license_status'),
        onboardingCompleted:
            ((json['onboarding_completed'] as num?)?.toInt() ?? 1) == 1,
      );
}
