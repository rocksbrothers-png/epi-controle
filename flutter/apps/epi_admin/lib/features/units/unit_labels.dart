/// Rótulos derivados da unidade — sem dependência de widget, para poderem ser
/// testados isoladamente.
///
/// A unidade carrega dois níveis da hierarquia acima dela: a empresa (tenant) e
/// o CNPJ (pessoa jurídica que responde fiscalmente por ela). Mostrar apenas a
/// empresa esconde justamente a informação que o Multi-CNPJ existe para expor.
library;

/// Nome curto do CNPJ da unidade: nome fantasia quando houver, senão razão
/// social, senão o próprio número. Vazio quando a unidade ainda não tem CNPJ
/// definido — estado legítimo durante a migração.
String legalEntityShortName(Map<String, dynamic> unit) {
  final trade = (unit['legal_entity_trade_name'] as String? ?? '').trim();
  if (trade.isNotEmpty) return trade;
  final legal = (unit['legal_entity_legal_name'] as String? ?? '').trim();
  if (legal.isNotEmpty) return legal;
  return (unit['legal_entity_cnpj'] as String? ?? '').trim();
}

/// Rótulo do CNPJ para a listagem: `Nome — 00.000.000/0001-00`.
///
/// Quando nome e número coincidem (só o número disponível), não repete.
String legalEntityLabel(Map<String, dynamic> unit) {
  final name = legalEntityShortName(unit);
  final cnpj = (unit['legal_entity_cnpj'] as String? ?? '').trim();
  if (name.isEmpty) return cnpj;
  if (cnpj.isEmpty || name == cnpj) return name;
  return '$name — $cnpj';
}

/// Subtítulo da unidade: empresa e CNPJ, separados por `·`, omitindo o que
/// estiver ausente. Unidade sem CNPJ continua mostrando a empresa em vez de um
/// separador solto.
String unitSubtitle(Map<String, dynamic> unit) {
  final parts = <String>[
    (unit['company_name'] as String? ?? '').trim(),
    legalEntityLabel(unit),
  ].where((p) => p.isNotEmpty);
  return parts.join(' · ');
}
