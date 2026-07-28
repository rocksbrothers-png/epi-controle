import 'package:epi_admin/features/units/unit_labels.dart';
import 'package:flutter_test/flutter_test.dart';

/// A listagem de unidades precisa mostrar **qual CNPJ** responde pela unidade.
/// Sem isso, a empresa com vários CNPJs vê uma lista em que todas as unidades
/// parecem iguais — e o Multi-CNPJ deixa de ser observável na tela onde ele
/// mais importa.
void main() {
  group('legalEntityShortName', () {
    test('prefere o nome fantasia', () {
      expect(
        legalEntityShortName({
          'legal_entity_trade_name': 'ACME Offshore',
          'legal_entity_legal_name': 'ACME Serviços Marítimos LTDA',
          'legal_entity_cnpj': '11.222.333/0001-81',
        }),
        'ACME Offshore',
      );
    });

    test('cai para a razão social quando não há nome fantasia', () {
      expect(
        legalEntityShortName({
          'legal_entity_trade_name': '  ',
          'legal_entity_legal_name': 'ACME Serviços Marítimos LTDA',
          'legal_entity_cnpj': '11.222.333/0001-81',
        }),
        'ACME Serviços Marítimos LTDA',
      );
    });

    test('cai para o número quando não há nome nenhum', () {
      expect(
        legalEntityShortName({'legal_entity_cnpj': '11.222.333/0001-81'}),
        '11.222.333/0001-81',
      );
    });

    test('unidade sem CNPJ devolve vazio, não "null"', () {
      expect(legalEntityShortName(const {}), '');
    });
  });

  group('legalEntityLabel', () {
    test('junta nome e número', () {
      expect(
        legalEntityLabel({
          'legal_entity_trade_name': 'ACME Offshore',
          'legal_entity_cnpj': '11.222.333/0001-81',
        }),
        'ACME Offshore — 11.222.333/0001-81',
      );
    });

    test('não repete o número quando ele é o único rótulo', () {
      expect(
        legalEntityLabel({'legal_entity_cnpj': '11.222.333/0001-81'}),
        '11.222.333/0001-81',
      );
    });
  });

  group('unitSubtitle', () {
    test('mostra empresa e CNPJ', () {
      expect(
        unitSubtitle({
          'company_name': 'Grupo ACME',
          'legal_entity_trade_name': 'ACME Offshore',
          'legal_entity_cnpj': '11.222.333/0001-81',
        }),
        'Grupo ACME · ACME Offshore — 11.222.333/0001-81',
      );
    });

    test('unidade sem CNPJ mostra só a empresa, sem separador solto', () {
      // Estado legítimo durante a migração. Um `·` pendurado no fim pareceria
      // dado corrompido para quem está olhando a tela.
      expect(unitSubtitle({'company_name': 'Grupo ACME'}), 'Grupo ACME');
    });

    test('sem empresa nem CNPJ devolve vazio (a tile esconde o subtítulo)', () {
      expect(unitSubtitle(const {}), '');
    });
  });
}
