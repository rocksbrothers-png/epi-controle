/// Modelo de assinatura exposto por `/api/subscriptions/*` (backend Python).
///
/// Fonte única de verdade no backend; aqui apenas desserializamos os campos
/// públicos (sem Access Token). Os nomes seguem o JSON do backend (snake_case).
class Subscription {
  const Subscription({
    required this.subscriptionId,
    required this.planKey,
    required this.paymentCycle,
    required this.paymentMethod,
    required this.status,
    required this.mpStatus,
    required this.amount,
    required this.currency,
    required this.renewalDate,
    required this.nextPaymentDate,
    required this.lastPaymentDate,
    required this.cancelDate,
    required this.cancelReason,
    required this.preapprovalId,
    required this.companyId,
    required this.tenantId,
    required this.createdAt,
  });

  final String subscriptionId;
  final String planKey;
  final String paymentCycle;
  final String paymentMethod;
  final String status;
  final String mpStatus;
  final double amount;
  final String currency;
  final String renewalDate;
  final String nextPaymentDate;
  final String lastPaymentDate;
  final String cancelDate;
  final String cancelReason;
  final String preapprovalId;
  final int? companyId;
  final String tenantId;
  final String createdAt;

  bool get isRecurring => paymentMethod == 'card';
  bool get isCancelled => status == 'cancelled' || status == 'canceled';
  bool get isActive => status == 'active' || status == 'authorized';

  static double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse('${value ?? ''}') ?? 0;
  }

  static int? _toIntOrNull(dynamic value) {
    if (value is int) return value;
    if (value == null) return null;
    return int.tryParse('$value');
  }

  factory Subscription.fromJson(Map<String, dynamic> json) {
    return Subscription(
      subscriptionId: (json['subscription_id'] ?? '').toString(),
      planKey: (json['plan_key'] ?? '').toString(),
      paymentCycle: (json['payment_cycle'] ?? '').toString(),
      paymentMethod: (json['payment_method'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      mpStatus: (json['mp_status'] ?? '').toString(),
      amount: _toDouble(json['amount']),
      currency: (json['currency'] ?? 'BRL').toString(),
      renewalDate: (json['renewal_date'] ?? '').toString(),
      nextPaymentDate: (json['next_payment_date'] ?? '').toString(),
      lastPaymentDate: (json['last_payment_date'] ?? '').toString(),
      cancelDate: (json['cancel_date'] ?? '').toString(),
      cancelReason: (json['cancel_reason'] ?? '').toString(),
      preapprovalId: (json['preapproval_id'] ?? '').toString(),
      companyId: _toIntOrNull(json['company_id']),
      tenantId: (json['tenant_id'] ?? '').toString(),
      createdAt: (json['created_at'] ?? '').toString(),
    );
  }
}

/// Fatura/cobrança individual (histórico financeiro — PR 6).
class Invoice {
  const Invoice({
    required this.subscriptionId,
    required this.mpPaymentId,
    required this.paymentMethod,
    required this.amount,
    required this.currency,
    required this.status,
    required this.dueDate,
    required this.paidAt,
    required this.receiptUrl,
    required this.invoiceUrl,
    required this.createdAt,
  });

  final String subscriptionId;
  final String mpPaymentId;
  final String paymentMethod;
  final double amount;
  final String currency;
  final String status;
  final String dueDate;
  final String paidAt;
  final String receiptUrl;
  final String invoiceUrl;
  final String createdAt;

  factory Invoice.fromJson(Map<String, dynamic> json) {
    return Invoice(
      subscriptionId: (json['subscription_id'] ?? '').toString(),
      mpPaymentId: (json['mp_payment_id'] ?? '').toString(),
      paymentMethod: (json['payment_method'] ?? '').toString(),
      amount: Subscription._toDouble(json['amount']),
      currency: (json['currency'] ?? 'BRL').toString(),
      status: (json['status'] ?? '').toString(),
      dueDate: (json['due_date'] ?? '').toString(),
      paidAt: (json['paid_at'] ?? '').toString(),
      receiptUrl: (json['receipt_url'] ?? '').toString(),
      invoiceUrl: (json['invoice_url'] ?? '').toString(),
      createdAt: (json['created_at'] ?? '').toString(),
    );
  }
}
