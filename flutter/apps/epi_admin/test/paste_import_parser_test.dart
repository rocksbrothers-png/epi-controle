import 'package:epi_admin/features/legal_entities/paste_import_dialog.dart';
import 'package:flutter_test/flutter_test.dart';

/// Parser da importação de CNPJs por colagem.
///
/// O mapeamento de cabeçalhos e a validação são do backend; aqui só garantimos
/// que o texto colado vira linhas fiéis ao que o usuário copiou.
void main() {
  group('parsePastedTable', () {
    test('lê colagem do Excel (separada por TAB)', () {
      final rows = parsePastedTable(
        'CNPJ\tRazão social\n11.222.333/0001-81\tACME SA\n45.723.174/0001-10\tFilial RJ',
      );
      expect(rows, hasLength(2));
      expect(rows.first['CNPJ'], '11.222.333/0001-81');
      expect(rows.first['Razão social'], 'ACME SA');
      expect(rows.last['Razão social'], 'Filial RJ');
    });

    test('lê CSV separado por vírgula', () {
      final rows = parsePastedTable(
        'cnpj,legal_name\n11.222.333/0001-81,ACME SA',
      );
      expect(rows.single['legal_name'], 'ACME SA');
    });

    test('lê CSV separado por ponto e vírgula (padrão pt-BR)', () {
      final rows = parsePastedTable(
        'cnpj;legal_name;uf\n11.222.333/0001-81;ACME SA;RJ',
      );
      expect(rows.single['uf'], 'RJ');
    });

    test('respeita vírgula dentro de campo entre aspas', () {
      final rows = parsePastedTable(
        'cnpj,legal_name\n11.222.333/0001-81,"ACME SA, Matriz"',
      );
      expect(rows.single['legal_name'], 'ACME SA, Matriz');
    });

    test('trata aspas escapadas dentro do campo', () {
      final rows = parsePastedTable(
        'cnpj,legal_name\n1,"ACME ""Brasil"" SA"',
      );
      expect(rows.single['legal_name'], 'ACME "Brasil" SA');
    });

    test('ignora linhas em branco no meio da planilha', () {
      final rows = parsePastedTable(
        'cnpj,legal_name\n1,ACME\n\n\n2,Filial',
      );
      expect(rows, hasLength(2));
    });

    test('preenche vazio quando a linha tem menos colunas que o cabeçalho', () {
      final rows = parsePastedTable(
        'cnpj,legal_name,uf\n1,ACME',
      );
      expect(rows.single['uf'], '');
    });

    test('devolve vazio sem linhas de dados', () {
      expect(parsePastedTable('cnpj,legal_name'), isEmpty);
      expect(parsePastedTable(''), isEmpty);
    });

    test('aceita quebras de linha CRLF', () {
      final rows = parsePastedTable(
        'cnpj,legal_name\r\n1,ACME\r\n2,Filial',
      );
      expect(rows, hasLength(2));
    });
  });
}
