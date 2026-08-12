import 'package:epi_admin/core/bloc/dashboard_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// Filtro em cascata do dashboard: Empresa → CNPJ → Unidade → Setor.
///
/// Os testes exercitam o **estado**, que é onde mora a regra da cascata
/// (`availableUnits` liga Unidade ao CNPJ via `legal_entity_id`).
void main() {
  const units = <Map<String, dynamic>>[
    {'id': 1, 'name': 'Matriz SP', 'legal_entity_id': 10},
    {'id': 2, 'name': 'Base Santos', 'legal_entity_id': 10},
    {'id': 3, 'name': 'Filial RJ', 'legal_entity_id': 20},
  ];

  const legalEntities = <Map<String, dynamic>>[
    {'id': 10, 'cnpj': '11.222.333/0001-81', 'legal_name': 'ACME SA'},
    {'id': 20, 'cnpj': '45.723.174/0001-10', 'legal_name': 'ACME Filial RJ'},
  ];

  group('DashboardState.availableUnits (cascata CNPJ → Unidade)', () {
    test('sem CNPJ selecionado devolve todas as unidades', () {
      const state = DashboardState(units: units, legalEntities: legalEntities);
      expect(state.availableUnits, hasLength(3));
    });

    test('com CNPJ selecionado devolve só as unidades daquele CNPJ', () {
      const state = DashboardState(
        units: units,
        legalEntities: legalEntities,
        selectedLegalEntityId: 10,
      );
      final names = state.availableUnits.map((u) => u['name']).toList();
      expect(names, ['Matriz SP', 'Base Santos']);
      expect(names, isNot(contains('Filial RJ')));
    });

    test('CNPJ sem unidades devolve lista vazia', () {
      const state = DashboardState(
        units: units,
        legalEntities: legalEntities,
        selectedLegalEntityId: 99,
      );
      expect(state.availableUnits, isEmpty);
    });

    test('unidade sem legal_entity_id não aparece sob nenhum CNPJ', () {
      // Caso da janela de migração: unidade ainda sem vínculo.
      const orphan = <Map<String, dynamic>>[
        {'id': 4, 'name': 'Sem CNPJ', 'legal_entity_id': null},
      ];
      const state = DashboardState(units: orphan, selectedLegalEntityId: 10);
      expect(state.availableUnits, isEmpty);
    });
  });

  group('DashboardState.hasActiveFilter', () {
    test('falso sem nenhuma seleção', () {
      expect(const DashboardState().hasActiveFilter, isFalse);
    });

    test('verdadeiro com qualquer nível selecionado', () {
      expect(
        const DashboardState(selectedLegalEntityId: 10).hasActiveFilter,
        isTrue,
      );
      expect(const DashboardState(selectedUnitId: 1).hasActiveFilter, isTrue);
      expect(
        const DashboardState(selectedSector: 'Operação').hasActiveFilter,
        isTrue,
      );
    });
  });

  group('DashboardCubit — cascata limpa os níveis abaixo', () {
    test('trocar de CNPJ limpa unidade e setor', () {
      final cubit = DashboardCubit();
      cubit.emit(const DashboardState(
        units: units,
        legalEntities: legalEntities,
        selectedLegalEntityId: 10,
        selectedUnitId: 2,
        selectedSector: 'Operação',
      ));

      cubit.selectLegalEntity(20);

      expect(cubit.state.selectedLegalEntityId, 20);
      // A unidade 2 pertence ao CNPJ 10; mantê-la selecionada produziria um
      // recorte incoerente.
      expect(cubit.state.selectedUnitId, isNull);
      expect(cubit.state.selectedSector, isNull);
    });

    test('trocar de unidade limpa o setor mas preserva o CNPJ', () {
      final cubit = DashboardCubit();
      cubit.emit(const DashboardState(
        units: units,
        legalEntities: legalEntities,
        selectedLegalEntityId: 10,
        selectedUnitId: 1,
        selectedSector: 'Operação',
      ));

      cubit.selectUnit(2);

      expect(cubit.state.selectedLegalEntityId, 10);
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.selectedSector, isNull);
    });

    test('clearFilters zera os três níveis', () {
      final cubit = DashboardCubit();
      cubit.emit(const DashboardState(
        units: units,
        selectedLegalEntityId: 10,
        selectedUnitId: 1,
        selectedSector: 'Operação',
      ));

      cubit.clearFilters();

      expect(cubit.state.hasActiveFilter, isFalse);
    });
  });

  group('DashboardCubit.isLockedProfile', () {
    test('só admin e user (Administrador Local / Gestor de EPI) travam', () {
      expect(DashboardCubit(role: 'admin').isLockedProfile, isTrue);
      expect(DashboardCubit(role: 'user').isLockedProfile, isTrue);
      // general_admin/registry_admin administram múltiplos CNPJs e a
      // hierarquia inteira (docs/PAPEIS_E_ATRIBUICOES.md #2/#3) — não travam.
      expect(DashboardCubit(role: 'general_admin').isLockedProfile, isFalse);
      expect(DashboardCubit(role: 'registry_admin').isLockedProfile, isFalse);
      expect(DashboardCubit(role: 'master_admin').isLockedProfile, isFalse);
      expect(DashboardCubit().isLockedProfile, isFalse);
    });
  });

  group('DashboardCubit — perfis travados (Administrador Local / Gestor de EPI)', () {
    // Achado no dashboard real (web): Gestor de EPI via "Todos" nos filtros
    // de CNPJ/Unidade e os KPIs somavam a empresa inteira, não só a própria
    // unidade. Estes testes travam a mesma regra no lado Flutter.
    test('user (Gestor de EPI) ignora seleção de CNPJ/Unidade — sempre a própria unidade', () {
      final cubit = DashboardCubit(role: 'user', operationalUnitId: 2);
      cubit.emit(const DashboardState(units: units, legalEntities: legalEntities));

      cubit.selectLegalEntity(20);
      // Unidade 2 pertence ao CNPJ 10 — a trava nunca aceita o CNPJ 20.
      expect(cubit.state.selectedLegalEntityId, 10);
      expect(cubit.state.selectedUnitId, 2);

      cubit.selectUnit(3);
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.selectedLegalEntityId, 10);

      cubit.clearFilters();
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.selectedLegalEntityId, 10);
      expect(cubit.state.hasActiveFilter, isTrue);
    });

    test('admin (Administrador Local) trava igual a user, na sua própria unidade', () {
      final cubit = DashboardCubit(role: 'admin', operationalUnitId: 3);
      cubit.emit(const DashboardState(units: units, legalEntities: legalEntities));

      cubit.selectUnit(1);

      expect(cubit.state.selectedUnitId, 3);
      expect(cubit.state.selectedLegalEntityId, 20); // unidade 3 -> CNPJ 20
    });

    test('general_admin continua livre (multi-CNPJ, sem trava)', () {
      final cubit = DashboardCubit(role: 'general_admin', operationalUnitId: 2);
      cubit.emit(const DashboardState(units: units, legalEntities: legalEntities));

      cubit.selectLegalEntity(20);

      expect(cubit.state.selectedLegalEntityId, 20);
      expect(cubit.state.selectedUnitId, isNull);
    });
  });
}
