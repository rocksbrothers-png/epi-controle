import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// A fila de sync offline usa `sqflite`, que **não existe no Flutter Web**.
///
/// Sem o guard `kIsWeb`, o listener de conectividade dispara `flush()` assim
/// que o app sobe, `SyncDatabase` chama `sqflite` e a exceção não tratada
/// aparece como "Uncaught Error" no console — em TODAS as telas, porque o
/// listener é global. Não é um defeito de uma tela; é o Web inteiro.
///
/// Este arquivo trava o guard em cada porta de entrada. Foi promovido do Lote 6
/// para o Lote 1 exatamente por causa desse alcance.
String _fonte() =>
    File('lib/core/sync/sync_service.dart').readAsStringSync();

/// Corpo de um método, do cabeçalho até o fechamento no mesmo nível de recuo.
String _corpo(String fonte, String assinatura) {
  final inicio = fonte.indexOf(assinatura);
  expect(inicio, isNot(-1), reason: 'método não encontrado: $assinatura');
  final resto = fonte.substring(inicio);
  final fim = resto.indexOf('\n  }');
  return fim == -1 ? resto : resto.substring(0, fim);
}

void main() {
  test('o guard kIsWeb é importado da fonte certa', () {
    // `kIsWeb` vem de `foundation`; importar `dart:io` para detectar
    // plataforma seria pior — `dart:io` nem compila no Web.
    expect(_fonte(),
        contains("import 'package:flutter/foundation.dart' show kIsWeb;"));
  });

  test('startListening não registra o listener no Web', () {
    // Este é o ponto crítico: o listener é global e dispara sozinho. Guardar
    // só o flush deixaria o registro acontecer e a falha voltaria por outro
    // caminho.
    final corpo = _corpo(_fonte(), 'void startListening()');
    final guard = corpo.indexOf('if (kIsWeb) return;');
    final listener = corpo.indexOf('onConnectivityChanged');
    expect(guard, isNot(-1), reason: 'startListening sem guard kIsWeb');
    expect(listener, isNot(-1));
    expect(guard, lessThan(listener),
        reason: 'o guard precisa vir antes de registrar o listener');
  });

  test('flush não toca no SyncDatabase no Web', () {
    // `flush()` também é chamado direto por telas, não só pelo listener —
    // por isso precisa do próprio guard, e não apenas herdar o de cima.
    final corpo = _corpo(_fonte(), 'Future<void> flush()');
    final guard = corpo.indexOf('if (kIsWeb) return;');
    final banco = corpo.indexOf('SyncDatabase.');
    expect(guard, isNot(-1), reason: 'flush sem guard kIsWeb');
    expect(banco, isNot(-1));
    expect(guard, lessThan(banco),
        reason: 'o guard precisa vir antes de qualquer acesso ao SyncDatabase');
  });

  test('nenhum acesso ao SyncDatabase fica fora de um método guardado', () {
    // Varredura de regressão: um método NOVO que toque o `SyncDatabase` e
    // esqueça o guard falha aqui, e não no navegador do usuário.
    //
    // O corte é simples de propósito: `\n  ` inicia um membro da classe no
    // nível de recuo do Dart formatado, então dividir por ele dá um bloco por
    // método. Uma heurística que eu consiga conferir a olho vale mais do que
    // um parser meia-boca que erra em silêncio.
    final blocos = _fonte().split(RegExp(r'\n  (?=[\w@])'));
    final desprotegidos = blocos
        .where((b) => b.contains('SyncDatabase.'))
        .where((b) => !b.contains('if (kIsWeb) return;'))
        .map((b) => b.split('\n').first.trim())
        .toList();
    expect(desprotegidos, isEmpty,
        reason: 'tocam SyncDatabase sem guard kIsWeb: $desprotegidos');
  });
}
