import 'dart:io';

import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// `FichaConfig.rastreabilidade` e o seu consumidor (Lote 2b da paridade).
///
/// O campo é o **rótulo de rastreabilidade impresso no rodapé da Ficha de
/// EPI** — um texto livre, tratado como `TEXT` pelo backend desde sempre.
/// Este repositório modelava o campo como `bool` e o oferecia como um
/// `SwitchListTile`, e o resultado não era um campo "lido errado": era um
/// documento de NR-6 corrompido.
///
/// O backend faz `str(payload.get('rastreabilidade') or DEFAULT).strip()`,
/// então o `Switch` produzia:
///
///   ligado    → `str(True)`  → o rodapé da ficha imprimia literalmente `True`
///   desligado → `False` é falsy → `or DEFAULT` restaurava o rótulo padrão
///
/// Ou seja: **nenhuma das duas posições fazia o que a tela prometia**, e a
/// posição "ligado" gravava lixo num documento legal. Model e consumidor
/// precisam mudar juntos — trocar só o model não compila.
String _readSettingsScreen() =>
    File('lib/features/settings/settings_screen.dart').readAsStringSync();

/// Corpo de uma classe, do cabeçalho até a próxima declaração de topo.
///
/// Fatiar por `split` no nome da classe arrastaria o resto do arquivo junto e
/// faria qualquer varredura passar por acidente.
String _classBody(String source, String className) {
  final start = source.indexOf('class $className');
  expect(start, isNot(-1), reason: 'classe $className não encontrada');
  final rest = source.substring(start + 1);
  final next = rest.indexOf('\nclass ');
  return next == -1 ? rest : rest.substring(0, next);
}

void main() {
  group('FichaConfig.rastreabilidade é String', () {
    test('parseia o rótulo real enviado pelo backend', () {
      final cfg = FichaConfig.fromJson(const {
        'titulo': 'Ficha de EPI',
        'rastreabilidade': 'Ficha Individual de Controle de EPI - Ver. 01',
      });
      expect(cfg.rastreabilidade, 'Ficha Individual de Controle de EPI - Ver. 01');
      expect(cfg.rastreabilidade, isA<String>());
    });

    test('bool legado não vira o texto "true"/"false" no rodapé', () {
      // Bases que passaram pela versão anterior podem ter um bool gravado.
      // O parse tolera, mas jamais devolve a representação textual do bool —
      // era exatamente isso que aparecia impresso na ficha.
      final ligado = FichaConfig.fromJson(const {'rastreabilidade': true});
      expect(ligado.rastreabilidade, isNotEmpty);
      expect(ligado.rastreabilidade.toLowerCase(), isNot('true'));

      final desligado = FichaConfig.fromJson(const {'rastreabilidade': false});
      expect(desligado.rastreabilidade.toLowerCase(), isNot('false'));
    });

    test('ausente vira string vazia, sem lançar', () {
      final cfg = FichaConfig.fromJson(const {});
      expect(cfg.rastreabilidade, '');
    });

    test('demais campos não regridem com a troca de tipo', () {
      final cfg = FichaConfig.fromJson(const {
        'titulo': 'Ficha de EPI',
        'declaracao': 'Declaro ter recebido os EPIs.',
        'observacoes': 'Uso obrigatório.',
        'rastreabilidade': 'R-01',
      });
      expect(cfg.titulo, 'Ficha de EPI');
      expect(cfg.declaracao, 'Declaro ter recebido os EPIs.');
      expect(cfg.observacoes, 'Uso obrigatório.');

      // `copyWith` de um campo não pode arrastar os outros junto.
      final so = cfg.copyWith(rastreabilidade: 'R-02');
      expect(so.rastreabilidade, 'R-02');
      expect(so.titulo, 'Ficha de EPI');
      expect(so.declaracao, 'Declaro ter recebido os EPIs.');
      expect(so.observacoes, 'Uso obrigatório.');
    });

    test('o que sobe para o backend é String, nunca bool', () {
      const cfg = FichaConfig(rastreabilidade: 'R-01');
      expect(cfg.toJson()['rastreabilidade'], isA<String>());
      expect(cfg.toJson()['rastreabilidade'], isNot(anyOf(true, false)));
    });
  });

  group('consumidor: _FichaConfigFormState', () {
    late String corpo;

    setUp(() => corpo = _classBody(_readSettingsScreen(), '_FichaConfigFormState'));

    test('trata rastreabilidade como texto editável', () {
      expect(corpo, contains('late final TextEditingController _rastreabilidade;'));
      expect(
        corpo,
        contains('TextEditingController(text: widget.config.rastreabilidade)'),
      );
    });

    test('não sobrou nenhum liga/desliga ligado ao campo', () {
      // O `Switch` é a origem do defeito: ele só sabe emitir bool.
      expect(corpo, isNot(contains('SwitchListTile')));
      expect(corpo, isNot(contains('value: _rastreabilidade')));
      expect(corpo, isNot(contains('late bool _rastreabilidade')));
    });

    test('envia o texto do controlador ao salvar', () {
      expect(corpo, contains('rastreabilidade: _rastreabilidade.text'));
    });

    test('o controlador é liberado no dispose', () {
      // Um `TextEditingController` sem `dispose` vaza — o campo antigo era um
      // `bool` e não tinha essa obrigação, então é uma regressão fácil.
      final dispose = corpo.substring(corpo.indexOf('void dispose()'));
      expect(dispose, contains('_rastreabilidade.dispose();'));
    });

    test('reidrata o campo quando a config muda', () {
      final did = corpo.substring(corpo.indexOf('void didUpdateWidget'));
      expect(did, contains('_rastreabilidade.text = widget.config.rastreabilidade;'));
    });
  });
}
