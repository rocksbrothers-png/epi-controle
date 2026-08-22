/// Padrão CORPORATIVO da faixa de atenção de estoque (#271-B1b).
///
/// É o degrau do meio da hierarquia de três níveis:
///
///     system_default (20%) → company_configured → unit_configured
///
/// O valor aqui é o EFETIVO da empresa — o que as Unidades sem configuração
/// própria herdam. Ele **não** substitui `effectiveAttentionPercentage` de um
/// `Epi`, que já é o valor resolvido daquela Unidade e pode vir de qualquer um
/// dos três degraus.
class CompanyAttentionSetting {
  const CompanyAttentionSetting({
    required this.companyId,
    required this.attentionPercentage,
    required this.source,
    required this.hasCompanyConfig,
    required this.systemDefaultPercentage,
    required this.maxPercentage,
  });

  /// `company_configured`: a empresa gravou um padrão.
  static const sourceCompanyConfigured = 'company_configured';

  /// `system_default`: a empresa nunca gravou; vale a constante do sistema.
  static const sourceSystemDefault = 'system_default';

  final int companyId;

  /// Percentual efetivo da empresa.
  ///
  /// `0` é valor VÁLIDO e significativo ("sem faixa de atenção, me avise só no
  /// crítico"). Nunca tratar como ausência: quem diz se existe configuração
  /// corporativa é [hasCompanyConfig], nunca a truthiness deste número.
  final int attentionPercentage;

  /// De onde o valor veio. Origem é do SERVIDOR, a cada resposta — nunca
  /// deduzida da ação que a tela acabou de executar.
  ///
  /// Salvar 20% e restaurar o padrão de 20% devolvem o MESMO número com
  /// origens opostas. Inferir a origem a partir do botão clicado apagaria
  /// exatamente a distinção que esta fatia existe para preservar.
  final String source;

  /// Se existe linha de configuração corporativa.
  ///
  /// Vem pronto do backend. É o que habilita/desabilita "Restaurar padrão":
  /// restaurar o que já é `system_default` não faria nada.
  final bool hasCompanyConfig;

  /// Padrão do sistema (hoje 20) — **do servidor**, não constante em Dart.
  ///
  /// Fixar o número aqui criaria uma segunda régua para o mesmo parâmetro, que
  /// é como as divergências da #271 começaram.
  final int systemDefaultPercentage;

  /// Teto aceito (hoje 100) — do servidor, pelo mesmo motivo. A validação no
  /// cliente é conveniência; a autoridade é o backend.
  final int maxPercentage;

  bool get isCompanyConfigured => source == sourceCompanyConfigured;
  bool get isSystemDefault => source == sourceSystemDefault;

  factory CompanyAttentionSetting.fromJson(Map<String, dynamic> json) =>
      CompanyAttentionSetting(
        companyId: (json['company_id'] as num?)?.toInt() ?? 0,
        attentionPercentage:
            (json['attention_percentage'] as num?)?.toInt() ?? 0,
        source: (json['source'] as String?) ?? '',
        // A resposta de gravar/restaurar não traz `has_company_config`; nesses
        // casos a origem já responde a mesma pergunta, e é ela que manda.
        hasCompanyConfig: (json['has_company_config'] as bool?) ??
            ((json['source'] as String?) == sourceCompanyConfigured),
        systemDefaultPercentage:
            (json['system_default_percentage'] as num?)?.toInt() ?? 0,
        maxPercentage: (json['max_percentage'] as num?)?.toInt() ?? 0,
      );

  /// Aplica a resposta de um POST preservando os limites lidos no GET.
  ///
  /// `POST` devolve valor e origem, mas não repete `system_default_percentage`
  /// nem `max_percentage`. Sem isto o teto viraria `0` depois de salvar e a
  /// validação passaria a recusar tudo.
  CompanyAttentionSetting mergeLimitsFrom(CompanyAttentionSetting other) =>
      CompanyAttentionSetting(
        companyId: companyId,
        attentionPercentage: attentionPercentage,
        source: source,
        hasCompanyConfig: hasCompanyConfig,
        systemDefaultPercentage: systemDefaultPercentage == 0
            ? other.systemDefaultPercentage
            : systemDefaultPercentage,
        maxPercentage:
            maxPercentage == 0 ? other.maxPercentage : maxPercentage,
      );
}
