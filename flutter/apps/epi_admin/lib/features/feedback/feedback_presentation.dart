import 'package:intl/intl.dart';

import '../../core/i18n/generated/app_localizations.dart';

/// Labels only: preserve API status codes and unknown values from newer servers.
String feedbackStatusLabel(String status, AppLocalizations l) =>
    switch (status) {
      'open' => l.feedbackStatusOpen,
      'in_review' || 'em análise' => l.statusInReview,
      'resolved' => l.feedbackStatusResolved,
      'closed' => l.feedbackStatusClosed,
      'rejected' => l.statusRejected,
      'recebido' => l.feedbackStatusReceived,
      'em_analise_gestor' => l.feedbackStatusManagerReview,
      'aguardando_hseq' => l.feedbackStatusAwaitingHseq,
      'analise_hseq_concluida' => l.feedbackStatusHseqCompleted,
      'encaminhado_administracao' => l.feedbackStatusForwardedAdmin,
      'aguardando_aprovacao_admin' => l.feedbackStatusAwaitingAdmin,
      'aprovado' || 'aprovada' => l.statusApproved,
      'reprovado' || 'rejeitada' => l.feedbackStatusNotApproved,
      'acao_corretiva_aberta' => l.feedbackStatusCorrectiveAction,
      'encerrado' => l.feedbackStatusEnded,
      'solicitada_mais_informacao' => l.feedbackStatusMoreInformation,
      'pendente' => l.statusPending,
      'arquivada' => l.safetyStateArchived,
      _ => status,
    };

/// Preserve the previous DateTime.parse timestamp normalization before formatting.
String formatFeedbackDate(String raw, String locale) {
  if (raw.isEmpty) return '';
  try {
    return DateFormat.yMd(locale).format(DateTime.parse(raw));
  } catch (_) {
    return raw;
  }
}
