import 'package:epi_admin/main.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato de resolução de `API_BASE_URL` (BP1 / EST-V1.6).
///
/// A regra vive em [resolveApiBaseUrl] (main.dart) justamente para ser testável
/// sem subir o app. O ponto central: **um build RELEASE nativo sem
/// `API_BASE_URL` falha explicitamente** em vez de cair em `localhost:5000` e
/// gerar um app publicado sem backend. Web e debug preservam o contrato antigo.
void main() {
  const define = 'https://backend.example.com';

  group('resolveApiBaseUrl', () {
    test('T1 — Web release sem define → same-origin (string vazia)', () {
      expect(
        resolveApiBaseUrl(
          isWeb: true,
          isDebugMode: false,
          isReleaseMode: true,
          apiBaseUrlDefine: '',
        ),
        '',
      );
    });

    test('T2 — Nativo debug sem define → localhost (contrato preservado)', () {
      expect(
        resolveApiBaseUrl(
          isWeb: false,
          isDebugMode: true,
          isReleaseMode: false,
          apiBaseUrlDefine: '',
        ),
        'http://localhost:5000',
      );
    });

    test('T3 — Nativo release com define → usa exatamente o define', () {
      expect(
        resolveApiBaseUrl(
          isWeb: false,
          isDebugMode: false,
          isReleaseMode: true,
          apiBaseUrlDefine: define,
        ),
        define,
      );
    });

    test('T4 — Nativo release sem define → FAIL-CLOSED (StateError)', () {
      expect(
        () => resolveApiBaseUrl(
          isWeb: false,
          isDebugMode: false,
          isReleaseMode: true,
          apiBaseUrlDefine: '',
        ),
        throwsStateError,
      );
    });

    test('Web debug sem define → localhost (dev web)', () {
      expect(
        resolveApiBaseUrl(
          isWeb: true,
          isDebugMode: true,
          isReleaseMode: false,
          apiBaseUrlDefine: '',
        ),
        'http://localhost:5000',
      );
    });

    test('Define sempre vence, em qualquer target/modo', () {
      for (final isWeb in [true, false]) {
        for (final isRelease in [true, false]) {
          expect(
            resolveApiBaseUrl(
              isWeb: isWeb,
              isDebugMode: !isRelease,
              isReleaseMode: isRelease,
              apiBaseUrlDefine: define,
            ),
            define,
          );
        }
      }
    });

    test('T10 — Web release NÃO é forçado a URL absoluta (segue same-origin)',
        () {
      // Garante que a correção de BP1 (nativo) não exigiu URL absoluta na Web.
      expect(
        resolveApiBaseUrl(
          isWeb: true,
          isDebugMode: false,
          isReleaseMode: true,
          apiBaseUrlDefine: '',
        ),
        isEmpty,
      );
    });

    test('Nativo profile sem define → localhost (não é release)', () {
      expect(
        resolveApiBaseUrl(
          isWeb: false,
          isDebugMode: false,
          isReleaseMode: false,
          apiBaseUrlDefine: '',
        ),
        'http://localhost:5000',
      );
    });
  });
}
