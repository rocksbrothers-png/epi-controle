// Divisor horizontal ou vertical com tokens do Design System EPI Controle.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';

class EpiDivider extends StatelessWidget {
  const EpiDivider({
    super.key,
    this.vertical   = false,
    this.thickness  = 1.0,
    this.color,
    this.indent     = 0.0,
    this.endIndent  = 0.0,
  });

  final bool   vertical;
  final double thickness;
  final Color? color;
  final double indent;
  final double endIndent;

  @override
  Widget build(BuildContext context) {
    final isDark       = Theme.of(context).brightness == Brightness.dark;
    final resolvedColor = color
        ?? (isDark ? EpiColors.darkBorder : EpiColors.border);

    if (vertical) {
      return VerticalDivider(
        thickness:  thickness,
        color:      resolvedColor,
        indent:     indent,
        endIndent:  endIndent,
        width:      thickness + indent + endIndent,
      );
    }

    return Divider(
      thickness: thickness,
      color:     resolvedColor,
      indent:    indent,
      endIndent: endIndent,
      height:    thickness,
    );
  }
}
