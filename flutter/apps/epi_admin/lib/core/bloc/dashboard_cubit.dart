import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';
import '../i18n/locale_provider.dart';

class DashboardState extends Equatable {
  const DashboardState({
    this.isLoading = false,
    this.error,
    this.deliveriesToday = 0,
    this.expiringEpis = 0,
    this.criticalStock = 0,
    this.pendingPurchases = 0,
    this.alerts = const [],
  });

  final bool isLoading;
  final String? error;
  final int deliveriesToday;
  final int expiringEpis;
  final int criticalStock;
  final int pendingPurchases;
  final List<Map<String, dynamic>> alerts;

  @override
  List<Object?> get props => [
        isLoading,
        error,
        deliveriesToday,
        expiringEpis,
        criticalStock,
        pendingPurchases,
        alerts,
      ];
}

class DashboardCubit extends Cubit<DashboardState> {
  DashboardCubit({this.localeProvider}) : super(const DashboardState());

  final LocaleProvider? localeProvider;

  Future<void> load() async {
    emit(const DashboardState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final now = DateTime.now();
      final thirtyDaysFromNow = now.add(const Duration(days: 30));

      // Apply locale preference from bootstrap
      if (localeProvider != null) {
        localeProvider!.applyUserPreference(
          bootstrap.preferredLocale,
          bootstrap.companyLocale,
        );
      }

      final expiringCount = bootstrap.epis.where((e) {
        final expiryStr = e['ca_expiry_date'] as String?;
        if (expiryStr == null) return false;
        final expiry = DateTime.tryParse(expiryStr);
        return expiry != null &&
            expiry.isAfter(now) &&
            expiry.isBefore(thirtyDaysFromNow);
      }).length;

      final criticalCount = bootstrap.epis.where((e) {
        final qty = (e['stock_quantity'] as num?)?.toInt() ?? 0;
        final min = (e['minimum_stock'] as num?)?.toInt() ?? 0;
        return qty <= min;
      }).length;

      // Count deliveries made today
      final todayStr =
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final deliveriesTodayCount = bootstrap.deliveries.where((d) {
        final dateStr = d['delivery_date'] as String? ??
            d['created_at'] as String? ??
            '';
        return dateStr.startsWith(todayStr);
      }).length;

      // Requisições de compra pendentes: agora vêm do bootstrap
      // (pending_purchases), já escopadas e gateadas por permissão no backend.
      emit(DashboardState(
        isLoading: false,
        deliveriesToday: deliveriesTodayCount,
        expiringEpis: expiringCount,
        criticalStock: criticalCount,
        pendingPurchases: bootstrap.pendingPurchases,
        alerts: bootstrap.alerts,
      ));
    } on Exception catch (e) {
      emit(DashboardState(isLoading: false, error: e.toString()));
    }
  }
}
