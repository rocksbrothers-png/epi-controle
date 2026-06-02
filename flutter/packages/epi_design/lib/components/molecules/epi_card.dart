// Card de superfície com borda e raio padronizados do Design System EPI Controle.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

class EpiCard extends StatelessWidget {
  const EpiCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.elevation = 0,
    this.color,
  });

  final Widget        child;
  final EdgeInsets?   padding;
  final VoidCallback? onTap;
  final double        elevation;
  final Color?        color;

  @override
  Widget build(BuildContext context) {
    final isDark       = Theme.of(context).brightness == Brightness.dark;
    final bgColor      = color ?? (isDark ? EpiColors.darkSurface : EpiColors.surface);
    final borderColor  = isDark ? EpiColors.darkBorder : EpiColors.border;
    final resolvedPad  = padding ?? const EdgeInsets.all(EpiSpacing.lg);

    final container = Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(EpiRadius.lg),
        border: Border.all(color: borderColor),
        boxShadow: elevation > 0
            ? [
                BoxShadow(
                  color: Colors.black.withOpacity(0.06 * elevation),
                  blurRadius: 4 * elevation,
                  offset: Offset(0, 2 * elevation),
                ),
              ]
            : null,
      ),
      child: Padding(padding: resolvedPad, child: child),
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: container,
      );
    }
    return container;
  }
}
