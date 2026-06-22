import '../database/sync_database.dart';

/// Fila de operações offline — abstrai o `SyncDatabase` (sqflite) para que os
/// cubits possam ser testados (caminhos de fila offline) sem platform channels.
abstract class OfflineQueue {
  Future<void> enqueue({
    required String opType,
    required Map<String, dynamic> payload,
  });
}

/// Implementação real: delega ao `SyncDatabase` (sqflite).
class SyncDatabaseQueue implements OfflineQueue {
  const SyncDatabaseQueue();

  @override
  Future<void> enqueue({
    required String opType,
    required Map<String, dynamic> payload,
  }) =>
      SyncDatabase.enqueue(opType: opType, payload: payload);
}
