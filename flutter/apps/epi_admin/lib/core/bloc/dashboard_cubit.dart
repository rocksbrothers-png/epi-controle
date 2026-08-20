import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';
import '../i18n/locale_provider.dart';

/// Carrega o resumo do painel. Injetável para que os testes exercitem a
/// cascata e os KPIs sem rede.
typedef DashboardSummaryLoader = Future<DashboardSummary> Function({
  int? legalEntityId,
  int? unitId,
  String? sector,
});

/// Estado do painel — **transporte** do que o servidor decidiu.
///
/// Até a fatia 1.1D-C2 este estado guardava as listas cruas do `/api/bootstrap`
/// (entregas, EPIs, colaboradores) e recomputava em Dart os KPIs, o recorte por
/// CNPJ/Unidade/Setor, os setores do dropdown e a dedução de perfil travado.
/// Agora tudo isso vem pronto de `GET /api/dashboard/summary`: o recorte é uma
/// resposta do servidor, não uma regra reimplementada aqui.
class DashboardState extends Equatable {
  const DashboardState({
    this.isLoading = false,
    this.error,
    this.scope = const DashboardScope(),
    this.kpis = const DashboardKpis(),
    this.filters = const DashboardFilters(),
    this.alerts = const [],
    this.compliance = const {},
  });

  final bool isLoading;
  final String? error;

  /// Contexto de Unidade RESOLVIDO PELO SERVIDOR, inclusive `locked`.
  final DashboardScope scope;

  final DashboardKpis kpis;

  /// Fontes do filtro em cascata, já escopadas por papel e tenant no backend.
  final DashboardFilters filters;

  final List<Map<String, dynamic>> alerts;

  /// Resumo de conformidade de estoque, repassado do backend sem interpretação.
  final Map<String, int> compliance;

  int get deliveriesToday => kpis.deliveriesToday;
  int get expiringEpis => kpis.expiringEpis;
  int get pendingPurchases => kpis.pendingPurchases;

  /// EPIs críticos na Unidade em escopo. `null` — nunca `0` — quando nenhuma
  /// Unidade foi resolvida: zero afirmaria "nenhum EPI crítico", e a pergunta
  /// simplesmente não se aplica a um recorte corporativo.
  int? get criticalStock => kpis.criticalStock;

  /// EPIs na faixa de atenção. Mesma semântica de `null` do anterior.
  int? get nearMinimumStock => kpis.nearMinimumStock;

  List<DashboardFilterOption> get legalEntities => filters.legalEntities;
  List<DashboardFilterOption> get units => filters.units;
  List<String> get sectors => filters.sectors;

  int? get selectedLegalEntityId => scope.legalEntityId;
  int? get selectedUnitId => scope.unitId;
  String? get selectedSector => scope.sector;

  /// Perfil travado numa única Unidade. **Vem do servidor** (`scope.locked`).
  /// Era deduzido com `role == 'admin' || role == 'user'` — autorização
  /// espelhada em Dart, que envelhecia separada do backend.
  bool get isLocked => scope.locked;

  /// Unidades exibíveis: com um CNPJ selecionado, só as dele.
  List<DashboardFilterOption> get availableUnits =>
      filters.unitsFor(selectedLegalEntityId);

  bool get hasActiveFilter =>
      selectedLegalEntityId != null ||
      selectedUnitId != null ||
      selectedSector != null;

  DashboardState _copyWith({
    bool? isLoading,
    String? error,
    DashboardSummary? summary,
  }) =>
      DashboardState(
        isLoading: isLoading ?? this.isLoading,
        // `error` NÃO cai no padrão `?? this.error`: omiti-lo limpa o erro.
        // Uma nova consulta começa sem a falha da anterior pendurada na tela.
        error: error,
        scope: summary?.scope ?? scope,
        kpis: summary?.kpis ?? kpis,
        filters: summary?.filters ?? filters,
        alerts: summary?.alerts ?? alerts,
        compliance: summary?.compliance ?? compliance,
      );

  @override
  List<Object?> get props => [
        isLoading,
        error,
        scope.unitId,
        scope.unitScopeSource,
        scope.locked,
        scope.legalEntityId,
        scope.sector,
        kpis.deliveriesToday,
        kpis.expiringEpis,
        kpis.criticalStock,
        kpis.nearMinimumStock,
        kpis.pendingPurchases,
        filters.legalEntities.map((e) => e.id).toList(),
        filters.units.map((u) => u.id).toList(),
        filters.sectors,
        alerts,
        compliance,
      ];
}

class DashboardCubit extends Cubit<DashboardState> {
  DashboardCubit({this.localeProvider, DashboardSummaryLoader? loader})
      : _loader = loader ?? _defaultLoader,
        super(const DashboardState());

  final LocaleProvider? localeProvider;
  final DashboardSummaryLoader _loader;

  static Future<DashboardSummary> _defaultLoader({
    int? legalEntityId,
    int? unitId,
    String? sector,
  }) =>
      ApiClient.dashboard.summary(
        actorUserId: ApiClient.actorUserId,
        legalEntityId: legalEntityId,
        unitId: unitId,
        sector: sector,
      );

  Future<void> load() async {
    await _applyLocale();
    await _fetch();
  }

  // ── Filtro em cascata: CNPJ → Unidade → Setor ────────────────────────────
  //
  // Cada troca consulta o servidor de novo. O recorte é dele: reaplicá-lo aqui
  // sobre dados crus foi o que fez o painel divergir do resto do sistema.
  //
  // Perfil travado não precisa de tratamento especial no cliente. O backend
  // ignora o `unit_id` pedido e devolve a Unidade do ator (`resolve_unit_scope`),
  // e a resposta chega com `scope.locked`.

  /// Seleciona o CNPJ. Limpa Unidade e setor: a cascata muda, e a Unidade
  /// escolhida pode não pertencer ao novo CNPJ.
  void selectLegalEntity(int? legalEntityId) =>
      _fetch(legalEntityId: legalEntityId);

  /// Seleciona a Unidade. Limpa o setor, que é o nível abaixo.
  void selectUnit(int? unitId) => _fetch(
        legalEntityId: state.selectedLegalEntityId,
        unitId: unitId,
      );

  void selectSector(String? sector) => _fetch(
        legalEntityId: state.selectedLegalEntityId,
        unitId: state.selectedUnitId,
        sector: sector,
      );

  void clearFilters() => _fetch();

  Future<void> _fetch({
    int? legalEntityId,
    int? unitId,
    String? sector,
  }) async {
    emit(state._copyWith(isLoading: true));
    try {
      final resumo = await _loader(
        legalEntityId: legalEntityId,
        unitId: unitId,
        sector: sector,
      );
      emit(state._copyWith(isLoading: false, summary: resumo));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// Preferência de idioma do usuário/empresa — única razão pela qual o painel
  /// ainda toca o `/api/bootstrap`. Falha silenciosa: o idioma padrão vale, e
  /// o painel não deve quebrar por causa dela.
  Future<void> _applyLocale() async {
    final provider = localeProvider;
    if (provider == null) return;
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      provider.applyUserPreference(
        bootstrap.preferredLocale,
        bootstrap.companyLocale,
      );
    } on Exception {
      return;
    }
  }
}
