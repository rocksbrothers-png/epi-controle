import 'dart:convert';

import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class SyncDatabase {
  static Database? _db;

  static Future<Database> get db async {
    _db ??= await _open();
    return _db!;
  }

  static Future<Database> _open() async {
    final path = join(await getDatabasesPath(), 'epi_sync.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: (db, _) => db.execute('''
        CREATE TABLE pending_ops (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          op_type TEXT NOT NULL,
          payload TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0
        )
      '''),
    );
  }

  static Future<int> enqueue({
    required String opType,
    required Map<String, dynamic> payload,
  }) async {
    final database = await db;
    return database.insert('pending_ops', {
      'op_type': opType,
      'payload': jsonEncode(payload),
      'created_at': DateTime.now().millisecondsSinceEpoch,
      'attempts': 0,
    });
  }

  static Future<List<Map<String, dynamic>>> pendingOps() async {
    final database = await db;
    return database.query('pending_ops', orderBy: 'created_at ASC');
  }

  static Future<void> delete(int id) async {
    final database = await db;
    await database.delete('pending_ops', where: 'id = ?', whereArgs: [id]);
  }

  static Future<void> incrementAttempts(int id) async {
    final database = await db;
    await database.rawUpdate(
      'UPDATE pending_ops SET attempts = attempts + 1 WHERE id = ?',
      [id],
    );
  }
}
