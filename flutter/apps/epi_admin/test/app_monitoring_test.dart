import 'package:epi_admin/core/observability/app_monitoring.dart';
import 'package:flutter_test/flutter_test.dart';

/// Sprint 4 — observabilidade. Valida contadores, caps (50/50/100) e FIFO.
void main() {
  late AppMonitoring m;

  setUp(() {
    m = AppMonitoring.instance..reset();
  });

  group('recordError', () {
    test('agrega por módulo', () {
      m.recordError('stock');
      m.recordError('stock');
      m.recordError('reports');
      final snap = m.snapshot();
      expect(snap.errorsByModule['stock'], 2);
      expect(snap.errorsByModule['reports'], 1);
      expect(snap.totalErrors, 3);
    });

    test('cap de módulos não impede incrementar os já registrados', () {
      for (var i = 0; i < AppMonitoring.maxModules; i++) {
        m.recordError('mod$i');
      }
      // novo módulo além do cap é ignorado
      m.recordError('overflow');
      expect(m.snapshot().errorsByModule.containsKey('overflow'), isFalse);
      // módulo existente continua contando
      m.recordError('mod0');
      expect(m.snapshot().errorsByModule['mod0'], 2);
      expect(m.snapshot().errorsByModule.length, AppMonitoring.maxModules);
    });
  });

  group('recordApiResult', () {
    test('ignora sucesso (2xx/3xx), conta 4xx/5xx/0 por endpoint:status', () {
      m.recordApiResult('/api/x', 200);
      m.recordApiResult('/api/x', 304);
      m.recordApiResult('/api/x', 500);
      m.recordApiResult('/api/x', 500);
      m.recordApiResult('/api/y', 0); // falha de rede
      final snap = m.snapshot();
      expect(snap.unstableApis.containsKey('/api/x:200'), isFalse);
      expect(snap.unstableApis['/api/x:500'], 2);
      expect(snap.unstableApis['/api/y:0'], 1);
    });

    test('cap de endpoints instáveis', () {
      for (var i = 0; i < AppMonitoring.maxApis; i++) {
        m.recordApiResult('/api/e$i', 500);
      }
      m.recordApiResult('/api/overflow', 500);
      expect(m.snapshot().unstableApis.containsKey('/api/overflow:500'), isFalse);
      expect(m.snapshot().unstableApiCount, AppMonitoring.maxApis);
    });
  });

  group('recordCritical (FIFO)', () {
    test('mantém no máximo maxCritical, descartando os mais antigos', () {
      for (var i = 0; i < AppMonitoring.maxCritical + 5; i++) {
        m.recordCritical('falha $i');
      }
      final snap = m.snapshot();
      expect(snap.criticalCount, AppMonitoring.maxCritical);
      // os 5 primeiros foram descartados → o mais antigo é 'falha 5'
      expect(snap.criticalFailures.first.message, 'falha 5');
      expect(snap.criticalFailures.last.message,
          'falha ${AppMonitoring.maxCritical + 4}');
    });
  });

  test('snapshot é imutável e reset limpa tudo', () {
    m.recordError('stock');
    m.recordApiResult('/api/x', 500);
    m.recordCritical('boom');
    final snap = m.snapshot();
    expect(() => snap.errorsByModule['x'] = 1, throwsUnsupportedError);

    m.reset();
    final after = m.snapshot();
    expect(after.totalErrors, 0);
    expect(after.unstableApiCount, 0);
    expect(after.criticalCount, 0);
  });
}
