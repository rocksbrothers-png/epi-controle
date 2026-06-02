// Wrapper de campo de formulário com label, helper e erro padronizados.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

class EpiFormField extends StatelessWidget {
  const EpiFormField({
    super.key,
    required this.label,
    required this.child,
    this.errorText,
    this.helperText,
    this.required = false,
  });

  final String  label;
  final Widget  child;
  final String? errorText;
  final String? helperText;
  final bool    required;

  @override
  Widget build(BuildContext context) {
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    final mutedColor = isDark ? const Color(0xFF8A9590) : EpiColors.textMuted;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Label row
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: EpiTypography.labelLarge.copyWith(color: mutedColor),
            ),
            if (required) ...[
              const SizedBox(width: EpiSpacing.xs),
              Text(
                '*',
                style: EpiTypography.labelLarge.copyWith(
                  color: EpiColors.danger,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: EpiSpacing.xs),
        child,
        if (errorText != null && errorText!.isNotEmpty) ...[
          const SizedBox(height: EpiSpacing.xs),
          Text(
            errorText!,
            style: EpiTypography.labelMedium.copyWith(color: EpiColors.danger),
          ),
        ] else if (helperText != null && helperText!.isNotEmpty) ...[
          const SizedBox(height: EpiSpacing.xs),
          Text(
            helperText!,
            style: EpiTypography.labelMedium.copyWith(color: mutedColor),
          ),
        ],
      ],
    );
  }
}
