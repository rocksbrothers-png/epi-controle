import 'package:flutter/material.dart';
import '../../tokens/colors.dart';

/// Classificação de estoque de um EPI **em uma Unidade** (#271).
///
/// Tipo próprio, separado de `EpiBadgeStatus`, de propósito: aquele descreve o
/// item no catálogo corporativo (ativo, vencido, sem estoque) e este descreve o
/// saldo naquela Unidade. Eram a mesma função antes da fatia 1.1D-C2, com duas
/// semânticas escondidas atrás do mesmo retorno; separar em dois tipos torna
/// impossível passar um pelo outro.
///
/// Os quatro valores são o espelho exato de `stock_status` do backend. Não
/// existe um quinto para "não sei": quando o servidor não classifica — porque
/// nenhuma Unidade foi resolvida — o valor é `null` e a tela **não desenha
/// badge nenhum**. Inventar aqui um estado neutro convidaria a tratá-lo como
/// `normal`, que é justamente a afirmação falsa que a #271 proíbe.
enum EpiStockStatus {
  /// Saldo acima da faixa de atenção.
  normal,

  /// Dentro da faixa de atenção: acima do mínimo, mas até `attention_limit`.
  nearMinimum,

  /// Saldo da Unidade <= mínimo daquela Unidade.
  critical,

  /// Monitoramento desligado para este par Unidade + EPI.
  ///
  /// **Nunca equivale a `normal`.** O EPI pode estar de fato crítico
  /// (`underlying_status`) e ainda assim aparecer aqui: o que está desligado é
  /// o alerta, não o problema. Por isso o cinza — ausência de vigilância, não
  /// afirmação de saúde.
  disabled,
}

/// Badge do estado de estoque por Unidade.
class EpiStockBadge extends StatelessWidget {
  const EpiStockBadge({super.key, required this.status, this.label});

  final EpiStockStatus status;
  final String? label;

  static String defaultLabel(EpiStockStatus s) => switch (s) {
        EpiStockStatus.normal => 'Normal',
        EpiStockStatus.nearMinimum => 'Próximo do mínimo',
        EpiStockStatus.critical => 'Crítico',
        EpiStockStatus.disabled => 'Alertas desativados',
      };

  /// Cor de destaque do estado. Exposta porque a mesma decisão pinta o número
  /// do saldo e a barra de progresso no card de estoque — replicar o `switch`
  /// nas telas é como as duas semânticas divergiram da primeira vez.
  static Color accentColor(EpiStockStatus s, BuildContext context) =>
      switch (s) {
        EpiStockStatus.normal => EpiColors.success,
        EpiStockStatus.nearMinimum => EpiColors.warning,
        EpiStockStatus.critical => EpiColors.danger,
        EpiStockStatus.disabled => Theme.of(context).colorScheme.outline,
      };

  (Color bg, Color text) _resolveColors(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = accentColor(status, context);
    if (status == EpiStockStatus.disabled) {
      final scheme = Theme.of(context).colorScheme;
      return (scheme.surfaceContainerHighest, scheme.outline);
    }
    return (isDark ? fg.withValues(alpha: 0.15) : _softLight(fg), fg);
  }

  static Color _softLight(Color base) => switch (base) {
        _ when base == EpiColors.success => EpiColors.successSoft,
        _ when base == EpiColors.danger => EpiColors.dangerSoft,
        _ when base == EpiColors.warning => EpiColors.warningSoft,
        _ => base.withValues(alpha: 0.12),
      };

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = _resolveColors(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration:
          BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(
        label ?? defaultLabel(status),
        style: Theme.of(context)
            .textTheme
            .labelSmall!
            .copyWith(color: fg, fontWeight: FontWeight.w600),
      ),
    );
  }
}
