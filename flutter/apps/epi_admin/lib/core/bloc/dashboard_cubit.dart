import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
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
    this.legalEntities = const [],
    this.units = const [],
    this.sectors = const [],
    this.selectedLegalEntityId,
    this.selectedUnitId,
    this.selectedSector,
  });

  final bool isLoading;
  final String? error;
  final int deliveriesToday;
  final int expiringEpis;
  final int criticalStock;
  final int pendingPurchases;
  final List<Map<String, dynamic>> alerts;

  /// Fontes do filtro em cascata Empresa → CNPJ → Unidade → Setor. Vêm do
  /// bootstrap, já escopadas por papel pelo backend.
  final List<Map<String, dynamic>> legalEntities;
  final List<Map<String, dynamic>> units;
  final List<String> sectors;

  final int? selectedLegalEntityId;
  final int? selectedUnitId;
  final String? selectedSector;

  /// Unidades exibíveis: quando um CNPJ está selecionado, só as dele. É o elo
  /// da cascata — a unidade pertence a um CNPJ (`units.legal_entity_id`).
  List<Map<String, dynamic>> get availableUnits {
    if (selectedLegalEntityId == null) return units;
    return units
        .where((u) => u['legal_entity_id'] == selectedLegalEntityId)
        .toList(growable: false);
  }

  bool get hasActiveFilter =>
      selectedLegalEntityId != null ||
      selectedUnitId != null ||
      selectedSector != null;

  @override
  List<Object?> get props => [
        isLoading,
        error,
        deliveriesToday,
        expiringEpis,
        criticalStock,
        pendingPurchases,
        alerts,
        legalEntities,
        units,
        sectors,
        selectedLegalEntityId,
        selectedUnitId,
        selectedSector,
      ];
}

class DashboardCubit extends Cubit<DashboardState> {
  DashboardCubit({this.localeProvider}) : super(const DashboardState());

  final LocaleProvider? localeProvider;

  // Dados crus do bootstrap: o filtro recomputa os KPIs localmente, sem nova
  // chamada de rede a cada troca de CNPJ/unidade/setor.
  List<Map<String, dynamic>> _rawDeliveries = const [];
  List<Map<String, dynamic>> _rawEpis = const [];
  List<Map<String, dynamic>> _rawEmployees = const [];
  int _rawPendingPurchases = 0;
  List<Map<String, dynamic>> _rawAlerts = const [];

  Future<void> load() async {
    emit(const DashboardState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final now = DateTime.now();

      // Apply locale preference from bootstrap
      if (localeProvider != null) {
        localeProvider!.applyUserPreference(
          bootstrap.preferredLocale,
          bootstrap.companyLocale,
        );
      }

      // Usa o modelo Epi (que entende as chaves canônicas do backend) para
      // computar os indicadores. "Vencendo" considera tanto o CA quanto a
      // validade do fabricante próximos do vencimento (NT 146/2015).
      final epis = bootstrap.epis.map(Epi.fromJson).toList();
      final expiringCount = epis
          .where((e) =>
              e.caStatus == 'expiring' ||
              e.manufacturerValidityStatus == 'expiring')
          .length;

      final criticalCount = epis.where((e) => e.isCriticalStock).length;

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
      _rawDeliveries = bootstrap.deliveries;
      _rawEpis = bootstrap.epis;
      _rawEmployees = bootstrap.employees;
      _rawPendingPurchases = bootstrap.pendingPurchases;
      _rawAlerts = bootstrap.alerts;

      emit(DashboardState(
        isLoading: false,
        deliveriesToday: deliveriesTodayCount,
        expiringEpis: expiringCount,
        criticalStock: criticalCount,
        pendingPurchases: bootstrap.pendingPurchases,
        alerts: bootstrap.alerts,
        legalEntities: bootstrap.legalEntities,
        units: bootstrap.units,
        sectors: _sectorsOf(bootstrap.employees),
      ));
    } on Exception catch (e) {
      emit(DashboardState(isLoading: false, error: e.toString()));
    }
  }

  // ── Filtro em cascata: Empresa → CNPJ → Unidade → Setor ──────────────────

  /// Seleciona o CNPJ. Limpa unidade e setor porque a cascata muda: a unidade
  /// escolhida pode não pertencer ao novo CNPJ.
  void selectLegalEntity(int? legalEntityId) => _applyFilter(
        legalEntityId: legalEntityId,
        unitId: null,
        sector: null,
      );

  /// Seleciona a unidade. Limpa o setor, que é o nível abaixo.
  void selectUnit(int? unitId) => _applyFilter(
        legalEntityId: state.selectedLegalEntityId,
        unitId: unitId,
        sector: null,
      );

  void selectSector(String? sector) => _applyFilter(
        legalEntityId: state.selectedLegalEntityId,
        unitId: state.selectedUnitId,
        sector: sector,
      );

  void clearFilters() => _applyFilter();

  /// Ids das unidades no escopo do filtro atual.
  ///
  /// Sem CNPJ nem unidade selecionados devolve `null`, que significa "sem
  /// restrição" — diferente de lista vazia, que significa "nenhuma unidade
  /// casa" e deve zerar os indicadores.
  Set<int>? _scopedUnitIds(int? legalEntityId, int? unitId) {
    if (unitId != null) return {unitId};
    if (legalEntityId == null) return null;
    return state.units
        .where((u) => u['legal_entity_id'] == legalEntityId)
        .map((u) => (u['id'] as num).toInt())
        .toSet();
  }

  void _applyFilter({int? legalEntityId, int? unitId, String? sector}) {
    final scopedUnits = _scopedUnitIds(legalEntityId, unitId);

    bool inScope(Object? rawUnitId) {
      if (scopedUnits == null) return true;
      if (rawUnitId is! num) return false;
      return scopedUnits.contains(rawUnitId.toInt());
    }

    final deliveries = _rawDeliveries.where((d) {
      if (!inScope(d['unit_id'])) return false;
      if (sector != null && '${d['sector'] ?? ''}' != sector) return false;
      return true;
    }).toList(growable: false);

    // EPI de nível empresa (unit_id nulo) permanece visível em qualquer
    // recorte: ele não pertence a uma unidade específica. Filtramos os mapas
    // crus porque o modelo Epi não expõe unit_id.
    final epis = _rawEpis
        .where((e) => e['unit_id'] == null || inScope(e['unit_id']))
        .map(Epi.fromJson)
        .toList(growable: false);

    final now = DateTime.now();
    final todayStr =
        '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';

    emit(DashboardState(
      isLoading: false,
      deliveriesToday: deliveries.where((d) {
        final dateStr =
            d['delivery_date'] as String? ?? d['created_at'] as String? ?? '';
        return dateStr.startsWith(todayStr);
      }).length,
      expiringEpis: epis
          .where((e) =>
              e.caStatus == 'expiring' ||
              e.manufacturerValidityStatus == 'expiring')
          .length,
      criticalStock: epis.where((e) => e.isCriticalStock).length,
      // Pendências de compra vêm agregadas do backend e não são recortáveis no
      // cliente; mantidas como estão para não exibir número inconsistente com
      // o filtro.
      pendingPurchases: _rawPendingPurchases,
      alerts: _rawAlerts,
      legalEntities: state.legalEntities,
      units: state.units,
      sectors: _sectorsOf(_rawEmployees, scopedUnits: scopedUnits),
      selectedLegalEntityId: legalEntityId,
      selectedUnitId: unitId,
      selectedSector: sector,
    ));
  }

  /// Setores distintos dos colaboradores no escopo, ordenados.
  static List<String> _sectorsOf(
    List<Map<String, dynamic>> employees, {
    Set<int>? scopedUnits,
  }) {
    final out = <String>{};
    for (final e in employees) {
      if (scopedUnits != null) {
        final unit = e['unit_id'];
        if (unit is! num || !scopedUnits.contains(unit.toInt())) continue;
      }
      final sector = '${e['sector'] ?? ''}'.trim();
      if (sector.isNotEmpty) out.add(sector);
    }
    return out.toList()..sort();
  }
}
