import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';

EpiBadgeStatus epiBadgeStatus(Epi epi) {
  if (epi.stockQuantity == 0) return EpiBadgeStatus.noStock;
  // A validade do fabricante rege a entrega do EPI (NT 146/2015); por isso o
  // status "vencido"/"vencendo" considera tanto o CA quanto a validade do
  // fabricante, priorizando o caso mais crítico.
  final caStatus = epi.caStatus;
  final manuStatus = epi.manufacturerValidityStatus;
  if (caStatus == 'expired' || manuStatus == 'expired') {
    return EpiBadgeStatus.expired;
  }
  if (caStatus == 'expiring' || manuStatus == 'expiring') {
    return EpiBadgeStatus.expiring;
  }
  return epi.isCriticalStock ? EpiBadgeStatus.critical : EpiBadgeStatus.active;
}
