import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';

import '../api/api_client.dart';
import '../database/sync_database.dart';

class SyncService {
  static final SyncService _instance = SyncService._();
  factory SyncService() => _instance;
  SyncService._();

  bool _syncing = false;

  void startListening() {
    Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) flush();
    });
  }

  Future<void> flush() async {
    if (_syncing) return;
    _syncing = true;
    try {
      final ops = await SyncDatabase.pendingOps();
      for (final op in ops) {
        final id = op['id'] as int;
        final type = op['op_type'] as String;
        final payload =
            jsonDecode(op['payload'] as String) as Map<String, dynamic>;
        try {
          await _execute(type, payload);
          await SyncDatabase.delete(id);
        } on Exception {
          await SyncDatabase.incrementAttempts(id);
        }
      }
    } finally {
      _syncing = false;
    }
  }

  Future<void> _execute(String type, Map<String, dynamic> payload) async {
    switch (type) {
      case 'stock_movement':
        await ApiClient.stock.recordMovement(
          actorUserId: payload['actor_user_id'] as int,
          companyId: payload['company_id'] as int,
          unitId: payload['unit_id'] as int,
          epiId: payload['epi_id'] as int,
          movementType: payload['movement_type'] as String,
          quantity: payload['quantity'] as int,
        );
      case 'delivery_create':
        await ApiClient.deliveries.createDelivery(
          companyId: payload['company_id'] as int,
          employeeId: payload['employee_id'] as int,
          epiId: payload['epi_id'] as int,
          quantity: payload['quantity'] as int,
          sector: payload['sector'] as String,
          roleName: payload['role_name'] as String,
          deliveryDate: payload['delivery_date'] as String,
          nextReplacementDate: payload['next_replacement_date'] as String,
          stockItemId: payload['stock_item_id'] as int,
          stockQrCode: payload['stock_qr_code'] as String,
          // A chave veio guardada com a operação: o reenvio é da mesma
          // entrega, e é isso que o backend precisa reconhecer.
          idempotencyKey: (payload['idempotency_key'] as String?) ?? '',
        );
      case 'devolution_create':
        await ApiClient.devolutions.createDevolution(
          deliveryId: payload['delivery_id'] as int,
          returnedDate: payload['returned_date'] as String,
          condition: payload['condition'] as String,
          destination: payload['destination'] as String,
          signatureData: payload['signature_data'] as String,
          notes: payload['notes'] as String?,
        );
    }
  }
}
