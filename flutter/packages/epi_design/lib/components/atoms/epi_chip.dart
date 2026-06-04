// Chip de seleção/filtro seguindo os tokens do Design System EPI Controle.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

class EpiChip extends StatelessWidget {
  const EpiChip({
    super.key,
    required this.label,
    this.selected = false,
    this.onTap,
    this.onDelete,
    this.color,
    this.icon,
  });

  final String        label;
  final bool          selected;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;
  final Color?        color;
  final IconData?     icon;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final resolvedColor = color ?? EpiColors.brand;

    final bgColor = selected
        ? (isDark ? resolvedColor.withValues(alpha: 0.2) : EpiColors.brandSoft)
        : (isDark ? EpiColors.darkSurface : EpiColors.surface);

    final borderColor = selected
        ? resolvedColor
        : (isDark ? EpiColors.darkBorder : EpiColors.border);

    final textColor = selected
        ? resolvedColor
        : (isDark ? const Color(0xFF8A9590) : EpiColors.textMuted);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: EpiSpacing.md,
          vertical: EpiSpacing.xs + 2,
        ),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(EpiRadius.full),
          border: Border.all(color: borderColor),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 14, color: textColor),
              const SizedBox(width: EpiSpacing.xs),
            ],
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium!.copyWith(
                color: textColor,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
            if (onDelete != null) ...[
              const SizedBox(width: EpiSpacing.xs),
              GestureDetector(
                onTap: onDelete,
                child: Icon(Icons.close_rounded, size: 14, color: textColor),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
