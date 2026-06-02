import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';

EpiBadgeStatus epiBadgeStatus(Epi epi) {
  if (epi.stockQuantity == 0) return EpiBadgeStatus.noStock;
  return switch (epi.caStatus) {
    'expired'  => EpiBadgeStatus.expired,
    'expiring' => EpiBadgeStatus.expiring,
    _          => epi.isCriticalStock ? EpiBadgeStatus.critical : EpiBadgeStatus.active,
  };
}
