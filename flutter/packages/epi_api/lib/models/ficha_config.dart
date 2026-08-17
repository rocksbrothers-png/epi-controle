class FichaConfig {
  const FichaConfig({
    this.titulo = '',
    this.declaracao = '',
    this.observacoes = '',
    this.rastreabilidade = '',
  });

  final String titulo;
  final String declaracao;
  final String observacoes;

  /// Rótulo de rastreabilidade impresso no rodapé da ficha (texto livre,
  /// ex.: "Ficha Individual de Controle de EPI - Ver. 01"). O backend trata
  /// como String — modelar como bool corrompia o rodapé com "true"/"false".
  final String rastreabilidade;

  factory FichaConfig.fromJson(Map<String, dynamic> json) => FichaConfig(
        titulo: json['titulo'] as String? ?? '',
        declaracao: json['declaracao'] as String? ?? '',
        observacoes: json['observacoes'] as String? ?? '',
        // Tolerante a bases onde um bool chegou a ser salvo pela versão antiga.
        rastreabilidade: switch (json['rastreabilidade']) {
          final String s => s,
          true => 'Ficha Individual de Controle de EPI - Ver. 01',
          _ => '',
        },
      );

  Map<String, dynamic> toJson() => {
        'titulo': titulo,
        'declaracao': declaracao,
        'observacoes': observacoes,
        'rastreabilidade': rastreabilidade,
      };

  FichaConfig copyWith({
    String? titulo,
    String? declaracao,
    String? observacoes,
    String? rastreabilidade,
  }) =>
      FichaConfig(
        titulo: titulo ?? this.titulo,
        declaracao: declaracao ?? this.declaracao,
        observacoes: observacoes ?? this.observacoes,
        rastreabilidade: rastreabilidade ?? this.rastreabilidade,
      );
}
