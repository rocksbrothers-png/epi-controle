import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Testes de contrato para os parsers de autenticação. Guardam os bugs reais
/// corrigidos no Sprint 1 do plano de migração Flutter:
///  - `permissions` e `refresh_token` vêm no **topo** da resposta de login
///    (antes eram lidos de `user['permissions']` / descartados);
///  - `/api/auth/refresh` rotaciona o refresh token;
///  - `/api/auth/me` devolve envelope `{success, data:{user, permissions}}`.
void main() {
  group('LoginResponse.fromJson', () {
    test('captura token, user, refresh_token e permissions de topo', () {
      final res = LoginResponse.fromJson(const {
        'token': 'access-123',
        'refresh_token': 'refresh-456',
        'permissions': ['users:view', 'epis:view'],
        'token_expires_in': 900,
        'user': {'id': 7, 'username': 'jefferson', 'role': 'general_admin'},
      });

      expect(res.token, 'access-123');
      expect(res.refreshToken, 'refresh-456');
      expect(res.permissions, ['users:view', 'epis:view']);
      expect(res.user['id'], 7);
      expect(res.user['role'], 'general_admin');
    });

    test('tolera ausência de refresh_token e permissions', () {
      final res = LoginResponse.fromJson(const {
        'token': 'access-only',
        'user': {'id': 1},
      });

      expect(res.token, 'access-only');
      expect(res.refreshToken, isNull);
      expect(res.permissions, isEmpty);
    });

    test('NÃO lê permissions de dentro de user (regressão do bug RBAC)', () {
      final res = LoginResponse.fromJson(const {
        'token': 't',
        'user': {'id': 1, 'permissions': ['should:ignore']},
      });

      // Permissões só valem quando no topo; o aninhamento em user é ignorado.
      expect(res.permissions, isEmpty);
    });
  });

  group('RefreshResponse.fromJson', () {
    test('captura access token e refresh rotacionado', () {
      final res = RefreshResponse.fromJson(const {
        'token': 'new-access',
        'refresh_token': 'rotated-refresh',
        'token_expires_in': 900,
      });

      expect(res.token, 'new-access');
      expect(res.refreshToken, 'rotated-refresh');
    });

    test('tolera refresh ausente (rotação opcional)', () {
      final res = RefreshResponse.fromJson(const {'token': 'new-access'});
      expect(res.token, 'new-access');
      expect(res.refreshToken, isNull);
    });
  });

  group('AuthIdentity.fromMeJson', () {
    test('desembrulha o envelope {success, data:{user, permissions}}', () {
      final id = AuthIdentity.fromMeJson(const {
        'success': true,
        'message': 'ok',
        'data': {
          'user': {'id': 9, 'username': 'ana'},
          'permissions': ['reports:view'],
        },
      });

      expect(id.user['id'], 9);
      expect(id.user['username'], 'ana');
      expect(id.permissions, ['reports:view']);
    });

    test('tolera formato plano {user, permissions} sem envelope', () {
      final id = AuthIdentity.fromMeJson(const {
        'user': {'id': 2},
        'permissions': ['stock:view'],
      });

      expect(id.user['id'], 2);
      expect(id.permissions, ['stock:view']);
    });
  });
}
</content>
