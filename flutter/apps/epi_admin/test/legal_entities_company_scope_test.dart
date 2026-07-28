import 'package:epi_admin/core/router/routes.dart';
import 'package:epi_admin/features/companies/companies_screen.dart';
import 'package:flutter_test/flutter_test.dart';

/// O Admin Master atende vários clientes e não tem empresa própria.
///
/// Antes disto, a tela de CNPJs sempre listava "a empresa do usuário" — o que,
/// para ele, não significava nada. A única forma de chegar aos CNPJs de um
/// cliente era digitar a URL com o `company_id` na mão.
void main() {
  group('rota de CNPJs recortada por empresa', () {
    test('leva o id da empresa', () {
      final uri = Uri.parse(legalEntitiesRouteForCompany(7, 'Grupo ACME'));
      expect(uri.path, Routes.legalEntities);
      expect(uri.queryParameters['company_id'], '7');
    });

    test('leva o nome para o título saber de quem são os CNPJs', () {
      final uri = Uri.parse(legalEntitiesRouteForCompany(7, 'Grupo ACME'));
      expect(uri.queryParameters['company_name'], 'Grupo ACME');
    });

    test('nome vazio não vira parâmetro vazio', () {
      // `company_name=` no fim da URL só polui; o título cai no rótulo padrão.
      final uri = Uri.parse(legalEntitiesRouteForCompany(7, '   '));
      expect(uri.queryParameters.containsKey('company_name'), isFalse);
      expect(uri.queryParameters['company_id'], '7');
    });

    test('nome com acento, & e espaço é escapado, não quebra a rota', () {
      // Razão social com "&" é comum ("Silva & Filhos"). Sem escape, tudo
      // depois do & viraria outro parâmetro e o nome chegaria truncado.
      final raw = 'Serviços & Cia — Filial SP';
      final uri = Uri.parse(legalEntitiesRouteForCompany(12, raw));
      expect(uri.queryParameters['company_name'], raw);
      expect(uri.path, Routes.legalEntities);
    });

    test('a rota continua sendo a mesma do menu, não uma tela paralela', () {
      // Uma segunda rota para "CNPJs do cliente" duplicaria a tela e as duas
      // divergiriam. O recorte é um parâmetro da mesma rota.
      expect(
        Uri.parse(legalEntitiesRouteForCompany(1, 'X')).path,
        Uri.parse(Routes.legalEntities).path,
      );
    });
  });
}
