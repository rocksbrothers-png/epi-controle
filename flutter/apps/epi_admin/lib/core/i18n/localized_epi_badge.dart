import 'package:epi_design/epi_design.dart';
import 'package:flutter/widgets.dart';

import 'generated/app_localizations.dart';

/// Supplies localized presentation while the existing badge owns status colors.
class LocalizedEpiBadge extends StatelessWidget {
  const LocalizedEpiBadge({super.key, required this.status});

  final EpiBadgeStatus status;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final label = switch (status) {
      EpiBadgeStatus.active => l.statusActive,
      EpiBadgeStatus.inactive => l.statusInactive,
      EpiBadgeStatus.expired => l.statusExpired,
      EpiBadgeStatus.expiring => l.statusExpiring,
      EpiBadgeStatus.pending => l.statusPending,
      EpiBadgeStatus.approved => l.statusApproved,
      EpiBadgeStatus.rejected => l.statusRejected,
      EpiBadgeStatus.inReview => l.statusInReview,
      EpiBadgeStatus.noStock => l.epiStatusNoStock,
      EpiBadgeStatus.critical => l.stockConfigStatusCritical,
    };
    return EpiBadge(status: status, label: label);
  }
}

/// Unit stock remains a separate classification from the catalog status above.
class LocalizedEpiStockBadge extends StatelessWidget {
  const LocalizedEpiStockBadge({super.key, required this.status});

  final EpiStockStatus status;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final label = switch (status) {
      EpiStockStatus.normal => l.stockConfigStatusNormal,
      EpiStockStatus.nearMinimum => l.stockConfigStatusNearMinimum,
      EpiStockStatus.critical => l.stockConfigStatusCritical,
      EpiStockStatus.disabled => l.stockConfigStatusDisabled,
    };
    return EpiStockBadge(status: status, label: label);
  }
}
