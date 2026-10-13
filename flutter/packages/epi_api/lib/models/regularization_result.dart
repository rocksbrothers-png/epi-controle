/// Resultado da regularização de validade física (EST-V3.5-R2), devolvido pelo
/// backend. A classificação é SEMPRE do servidor — o cliente apenas EXIBE este
/// resultado, inclusive quando a regularização resulta em bloqueio por
/// vencimento. Não há cálculo de validade no Flutter.
class RegularizationResult {
  const RegularizationResult({
    required this.status,
    required this.validityStatus,
    required this.physicalExpiryDate,
    required this.eligible,
    required this.blockedExpired,
    required this.idempotent,
    required this.message,
  });

  /// Status operacional final da peça (ex.: in_stock, blocked_expired).
  final String status;

  /// Classificação da validade física calculada pelo backend
  /// (valid / expiring / expired / unknown).
  final String validityStatus;
  final String physicalExpiryDate;
  final bool eligible;
  final bool blockedExpired;
  final bool idempotent;

  /// Mensagem pronta do backend (inclui o caso de bloqueio por vencimento).
  final String message;

  factory RegularizationResult.fromJson(Map<String, dynamic> json) =>
      RegularizationResult(
        status: (json['status'] as String?) ?? '',
        validityStatus: (json['validity_status'] as String?) ?? '',
        physicalExpiryDate: (json['physical_expiry_date'] as String?) ?? '',
        eligible: (json['eligible'] as bool?) ?? false,
        blockedExpired: (json['blocked_expired'] as bool?) ?? false,
        idempotent: (json['idempotent'] as bool?) ?? false,
        message: (json['message'] as String?) ?? '',
      );
}
