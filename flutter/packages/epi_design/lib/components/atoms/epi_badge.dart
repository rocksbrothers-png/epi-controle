import 'package:flutter/material.dart';
import '../../tokens/colors.dart';

enum EpiBadgeStatus {
  active, inactive, expired, expiring, pending,
  approved, rejected, inReview, noStock, critical,
}

class EpiBadge extends StatelessWidget {
  const EpiBadge({super.key, required this.status, this.label});

  final EpiBadgeStatus status;
  final String?        label;

  static String defaultLabel(EpiBadgeStatus s) => switch (s) {
    EpiBadgeStatus.active   => 'Ativo',
    EpiBadgeStatus.inactive => 'Inativo',
    EpiBadgeStatus.expired  => 'Vencido',
    EpiBadgeStatus.expiring => 'Vencendo',
    EpiBadgeStatus.pending  => 'Pendente',
    EpiBadgeStatus.approved => 'Aprovado',
    EpiBadgeStatus.rejected => 'Rejeitado',
    EpiBadgeStatus.inReview => 'Em análise',
    EpiBadgeStatus.noStock  => 'Sem estoque',
    EpiBadgeStatus.critical => 'Crítico',
  };

  (Color bg, Color text) get _colors => switch (status) {
    EpiBadgeStatus.active   => (EpiColors.successSoft, EpiColors.success),
    EpiBadgeStatus.inactive => (EpiColors.border,      EpiColors.textMuted),
    EpiBadgeStatus.expired  => (EpiColors.dangerSoft,  EpiColors.danger),
    EpiBadgeStatus.expiring => (EpiColors.warningSoft, EpiColors.warning),
    EpiBadgeStatus.pending  => (EpiColors.warningSoft, EpiColors.warning),
    EpiBadgeStatus.approved => (EpiColors.successSoft, EpiColors.success),
    EpiBadgeStatus.rejected => (EpiColors.dangerSoft,  EpiColors.danger),
    EpiBadgeStatus.inReview => (EpiColors.infoSoft,    EpiColors.info),
    EpiBadgeStatus.noStock  => (EpiColors.border,      EpiColors.textMuted),
    EpiBadgeStatus.critical => (EpiColors.dangerSoft,  EpiColors.danger),
  };

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = _colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(
        label ?? defaultLabel(status),
        style: Theme.of(context).textTheme.labelSmall!.copyWith(color: fg, fontWeight: FontWeight.w600),
      ),
    );
  }
}
