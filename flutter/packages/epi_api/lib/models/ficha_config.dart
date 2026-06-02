class FichaConfig {
  const FichaConfig({
    this.titulo = '',
    this.declaracao = '',
    this.observacoes = '',
    this.rastreabilidade = false,
  });

  final String titulo;
  final String declaracao;
  final String observacoes;
  final bool rastreabilidade;

  factory FichaConfig.fromJson(Map<String, dynamic> json) => FichaConfig(
        titulo: json['titulo'] as String? ?? '',
        declaracao: json['declaracao'] as String? ?? '',
        observacoes: json['observacoes'] as String? ?? '',
        rastreabilidade: (json['rastreabilidade'] as bool?) ?? false,
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
    bool? rastreabilidade,
  }) =>
      FichaConfig(
        titulo: titulo ?? this.titulo,
        declaracao: declaracao ?? this.declaracao,
        observacoes: observacoes ?? this.observacoes,
        rastreabilidade: rastreabilidade ?? this.rastreabilidade,
      );
}
