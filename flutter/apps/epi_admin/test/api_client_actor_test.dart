import 'dart:convert';

import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/session/session_context.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// `actor_user_id` precisa ser **o usuário da sessão**.
///
/// O backend compara este valor com o `sub` do JWT e responde 401 "Dados de
/// autenticação inconsistentes" quando divergem. Foi assim que a tela de CNPJs
/// aparecia vazia: ela mandava `actor_user_id=0` porque o ator só era definido
/// como efeito colateral de abrir a tela de Colaboradores — e, mesmo lá, com o
/// **primeiro usuário da empresa** em vez de quem estava logado.
/// Mesma chave usada por `ApiClient` para persistir a sessão.
const _kSessionContextKey = 'session_context';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // Os campos de `ApiClient` são `late final`: o init só pode rodar uma vez
  // por processo de teste. O baseUrl é irrelevante — nada aqui faz rede.
  setUpAll(() => ApiClient.init(baseUrl: 'http://localhost'));

  // `flutter_secure_storage` fala com a plataforma; em teste, um Map em memória.
  final store = <String, String>{};
  setUp(() {
    store.clear();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async {
        switch (call.method) {
          case 'write':
            store[call.arguments['key'] as String] =
                call.arguments['value'] as String;
            return null;
          case 'read':
            return store[call.arguments['key'] as String];
          case 'delete':
            store.remove(call.arguments['key'] as String);
            return null;
          case 'readAll':
            return store;
          case 'deleteAll':
            store.clear();
            return null;
        }
        return null;
      },
    );
  });

  SessionContext contextFor(int? userId) => SessionContext(
        userId: userId,
        companyId: 1,
        unitId: null,
        role: 'general_admin',
        permissions: const ['legal_entities:view'],
        tenantName: 'ACME',
        companySettings: const {},
      );

  test('salvar a sessão define o ator', () async {
    await ApiClient.saveSessionContext(contextFor(42));
    expect(ApiClient.actorUserId, 42);
  });

  test('restaurar a sessão do armazenamento define o ator', () async {
    // Modela o app reaberto: a sessão está no armazenamento, mas nada foi
    // gravado nesta execução. Quem já estava logado e abria CNPJs direto caía
    // exatamente aqui — e mandava 0.
    //
    // O JSON é semeado direto no storage (e não por `saveSessionContext`) de
    // propósito: passar pelo gravador definiria o ator e o teste não provaria
    // nada sobre a leitura.
    await ApiClient.saveSessionContext(contextFor(42));
    store[_kSessionContextKey] = jsonEncode(contextFor(77).toJson());

    final restored = await ApiClient.getSessionContext();
    expect(restored.userId, 77);
    expect(ApiClient.actorUserId, 77);
  });

  test('encerrar a sessão zera o ator', () async {
    await ApiClient.saveSessionContext(contextFor(42));
    await ApiClient.clearSession();
    expect(
      ApiClient.actorUserId,
      0,
      reason: 'ator remanescente vazaria o usuário anterior para a próxima sessão',
    );
  });

  test('sessão sem usuário não inventa um ator', () async {
    await ApiClient.saveSessionContext(contextFor(null));
    expect(ApiClient.actorUserId, 0);
  });
}
