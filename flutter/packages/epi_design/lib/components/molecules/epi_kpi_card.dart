import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

class EpiKpiCard extends StatelessWidget {
  const EpiKpiCard({
    super.key,
    required this.label,
    required this.value,
    this.icon,
    this.iconColor,
    this.delta,
    this.deltaPositive,
    this.onTap,
  });

  final String       label;
  final String       value;
  final IconData?    icon;
  final Color?       iconColor;
  final String?      delta;
  final bool?        deltaPositive;
  final VoidCallback?onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(EpiSpacing.md),
          border: Border.all(color: theme.colorScheme.surfaceContainerHighest),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (icon != null)
                  Container(
                    padding: const EdgeInsets.all(EpiSpacing.sm),
                    decoration: BoxDecoration(
                      color: (iconColor ?? EpiColors.brand).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(EpiSpacing.sm),
                    ),
                    child: Icon(icon, size: 20, color: iconColor ?? EpiColors.brand),
                  ),
                if (icon != null) const SizedBox(width: EpiSpacing.sm),
                Expanded(
                  child: Text(
                    label,
                    style: theme.textTheme.bodySmall,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: EpiSpacing.md),
            Text(
              value,
              style: theme.textTheme.displayMedium!.copyWith(
                fontWeight: FontWeight.w700,
                color: theme.colorScheme.onSurface,
              ),
            ),
            if (delta != null) ...[
              const SizedBox(height: EpiSpacing.xs),
              Row(
                children: [
                  Icon(
                    deltaPositive == true
                        ? Icons.trending_up_rounded
                        : Icons.trending_down_rounded,
                    size: 14,
                    color: deltaPositive == true ? EpiColors.success : EpiColors.danger,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    delta!,
                    style: theme.textTheme.labelSmall!.copyWith(
                      color: deltaPositive == true ? EpiColors.success : EpiColors.danger,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
