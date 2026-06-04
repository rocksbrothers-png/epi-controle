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

  (Color bg, Color text) _resolveColors(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    Color soft(Color base) =>
        isDark ? base.withValues(alpha: 0.15) : _softLight(base);
    return switch (status) {
      EpiBadgeStatus.active   => (soft(EpiColors.success), EpiColors.success),
      EpiBadgeStatus.inactive => _neutral(context),
      EpiBadgeStatus.expired  => (soft(EpiColors.danger),  EpiColors.danger),
      EpiBadgeStatus.expiring => (soft(EpiColors.warning), EpiColors.warning),
      EpiBadgeStatus.pending  => (soft(EpiColors.warning), EpiColors.warning),
      EpiBadgeStatus.approved => (soft(EpiColors.success), EpiColors.success),
      EpiBadgeStatus.rejected => (soft(EpiColors.danger),  EpiColors.danger),
      EpiBadgeStatus.inReview => (soft(EpiColors.info),    EpiColors.info),
      EpiBadgeStatus.noStock  => _neutral(context),
      EpiBadgeStatus.critical => (soft(EpiColors.danger),  EpiColors.danger),
    };
  }

  static Color _softLight(Color base) => switch (base) {
    _ when base == EpiColors.success => EpiColors.successSoft,
    _ when base == EpiColors.danger  => EpiColors.dangerSoft,
    _ when base == EpiColors.warning => EpiColors.warningSoft,
    _ when base == EpiColors.info    => EpiColors.infoSoft,
    _                                => base.withValues(alpha: 0.12),
  };

  static (Color, Color) _neutral(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return (scheme.surfaceContainerHighest, scheme.outline);
  }

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = _resolveColors(context);
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
