import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final contextJson = Platform.environment['EST35_HTTP_CONTEXT_JSON'];
  final token = Platform.environment['EST35_HTTP_TOKEN'];
  test(
    'real application HTTP, JWT and PostgreSQL physical stock contract',
    () async {
      final config = jsonDecode(contextJson!) as Map<String, dynamic>;
      final dio = Dio(
        BaseOptions(
          baseUrl: config['base_url'] as String,
          headers: {'Authorization': 'Bearer $token'},
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );
      final stock = StockApi(dio);
      final actor = config['actor_id'] as int;
      final unit = config['unit_id'] as int;
      final epiId = config['epi_id'] as int;
      final epis = await stock.fetchUnitStockEpis(
        actorUserId: actor,
        unitId: unit,
      );
      final epi = epis.singleWhere((e) => e.id == epiId);
      expect(epi.physicalValiditySummary?.expired, 1);
      expect(epi.physicalValiditySummary?.unknown, 1);
      expect(epi.availableQuantity, 1);
      final state = StockState(epis: [epi]);
      expect(state.manufacturerExpiredCount, 1);
      expect(state.manufacturerUnknownCount, 1);
      final candidates = await stock.fetchUnitAvailableItems(
        actorUserId: actor,
        unitId: unit,
        epiId: epiId,
      );
      final valid = config['valid_item'] as Map<String, dynamic>;
      final unknown = config['unknown_item'] as Map<String, dynamic>;
      expect(candidates.map((e) => e.id), [valid['id']]);
      expect(candidates.single.isEligibleCandidate, isTrue);
      final lookup = await stock.lookupQr(
        actorUserId: actor,
        unitId: unit,
        qrCode: unknown['qr'] as String,
      );
      expect(lookup.physicalExpiryDate, isNull);
      expect(lookup.isEligibleCandidate, isFalse);
      await expectLater(
        stock.lookupQr(
          actorUserId: actor,
          unitId: unit,
          qrCode: config['foreign_qr'] as String,
        ),
        throwsA(
          isA<DioException>().having(
            (e) => e.response?.statusCode,
            'foreign tenant refused',
            400,
          ),
        ),
      );
      final payload = {
        'actor_user_id': actor,
        'company_id': config['company_id'],
        'unit_id': unit,
        'employee_id': config['employee_id'],
        'epi_id': epiId,
        'quantity': 1,
        'stock_item_id': unknown['id'],
        'stock_qr_code': unknown['qr'],
        'sector': 'QA',
        'role_name': 'QA',
        'delivery_date': config['today'],
        'next_replacement_date': config['future'],
      };
      await expectLater(
        dio.post<dynamic>('/api/deliveries', data: payload),
        throwsA(
          isA<DioException>().having(
            (e) => e.response?.statusCode,
            'unknown physical expiry refused',
            400,
          ),
        ),
      );
      final after = await stock.fetchUnitStockEpis(
        actorUserId: actor,
        unitId: unit,
      );
      expect(
        after.singleWhere((e) => e.id == epiId).unitStockQuantity,
        epi.unitStockQuantity,
      );
      dio.close(force: true);
    },
    skip: contextJson == null || token == null
        ? 'Requires the isolated HTTP/PostgreSQL fixture; executed by Stock Validity Integration CI'
        : false,
  );
}
