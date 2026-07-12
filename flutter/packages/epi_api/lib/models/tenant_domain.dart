/// Domínio registrado da tenant (`/api/my-company/domains`).
///
/// Tipos: `platform_subdomain` (empresa.epicontrole.com.br, auto-verificado),
/// `custom_subdomain` e `custom_domain` (exigem CNAME + TXT de propriedade).
class TenantDomain {
  const TenantDomain({
    required this.id,
    required this.domain,
    required this.domainType,
    this.fullHost = '',
    this.typeLabel = '',
    this.verificationStatus = 'pending',
    this.sslStatus = 'pending',
    this.verificationToken = '',
    this.cnameTarget = '',
    this.txtRecord = '',
    this.isPrimary = false,
  });

  final int id;
  final String domain;
  final String domainType;
  final String fullHost;
  final String typeLabel;
  final String verificationStatus;
  final String sslStatus;
  final String verificationToken;
  final String cnameTarget;
  final String txtRecord;
  final bool isPrimary;

  bool get isVerified => verificationStatus == 'verified';

  factory TenantDomain.fromJson(Map<String, dynamic> json) => TenantDomain(
        id: (json['id'] as num?)?.toInt() ?? 0,
        domain: (json['domain'] as String?) ?? '',
        domainType: (json['domain_type'] as String?) ?? 'custom_domain',
        fullHost: (json['full_host'] as String?) ?? '',
        typeLabel: (json['type_label'] as String?) ?? '',
        verificationStatus:
            (json['verification_status'] as String?) ?? 'pending',
        sslStatus: (json['ssl_status'] as String?) ?? 'pending',
        verificationToken: (json['verification_token'] as String?) ?? '',
        cnameTarget: (json['cname_target'] as String?) ?? '',
        txtRecord: (json['txt_record'] as String?) ?? '',
        isPrimary: ((json['is_primary'] as num?)?.toInt() ?? 0) == 1,
      );
}
