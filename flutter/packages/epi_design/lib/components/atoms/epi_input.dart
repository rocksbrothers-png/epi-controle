// Campo de texto estilizado seguindo os tokens do Design System EPI Controle.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

enum EpiInputVariant { standard, search }

class EpiInput extends StatelessWidget {
  const EpiInput({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.onChanged,
    this.errorText,
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.keyboardType,
    this.enabled = true,
    this.maxLines = 1,
    this.onTap,
    this.readOnly = false,
    this.variant = EpiInputVariant.standard,
    this.focusNode,
    this.textInputAction,
    this.onSubmitted,
  });

  final String?                label;
  final String?                hint;
  final TextEditingController? controller;
  final ValueChanged<String>?  onChanged;
  final String?                errorText;
  final IconData?              prefixIcon;
  final Widget?                suffixIcon;
  final bool                   obscureText;
  final TextInputType?         keyboardType;
  final bool                   enabled;
  final int                    maxLines;
  final VoidCallback?          onTap;
  final bool                   readOnly;
  final EpiInputVariant        variant;
  final FocusNode?             focusNode;
  final TextInputAction?       textInputAction;
  final ValueChanged<String>?  onSubmitted;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;
    final fillColor   = isDark ? EpiColors.darkSurface : EpiColors.surface;

    Widget? resolvedPrefix;
    if (variant == EpiInputVariant.search) {
      resolvedPrefix = const Icon(Icons.search_rounded, size: 20, color: EpiColors.textMuted);
    } else if (prefixIcon != null) {
      resolvedPrefix = Icon(prefixIcon, size: 20, color: EpiColors.textMuted);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: Theme.of(context).textTheme.labelLarge!.copyWith(
              color: isDark ? const Color(0xFF8A9590) : EpiColors.textMuted,
            ),
          ),
          const SizedBox(height: EpiSpacing.xs),
        ],
        TextField(
          controller: controller,
          onChanged: onChanged,
          obscureText: obscureText,
          keyboardType: keyboardType,
          enabled: enabled,
          maxLines: obscureText ? 1 : maxLines,
          onTap: onTap,
          readOnly: readOnly,
          focusNode: focusNode,
          textInputAction: textInputAction,
          onSubmitted: onSubmitted,
          style: Theme.of(context).textTheme.bodyMedium,
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            prefixIcon: resolvedPrefix != null
                ? Padding(
                    padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.md),
                    child: resolvedPrefix,
                  )
                : null,
            prefixIconConstraints: resolvedPrefix != null
                ? const BoxConstraints(minWidth: 44, minHeight: 44)
                : null,
            suffixIcon: suffixIcon,
            filled: true,
            fillColor: enabled ? fillColor : fillColor.withValues(alpha: 0.6),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.lg,
              vertical: EpiSpacing.md,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: BorderSide(color: borderColor),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: BorderSide(color: borderColor),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: const BorderSide(color: EpiColors.brand, width: 1.5),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: const BorderSide(color: EpiColors.danger),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: const BorderSide(color: EpiColors.danger, width: 1.5),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              borderSide: BorderSide(color: borderColor.withValues(alpha: 0.5)),
            ),
          ),
        ),
      ],
    );
  }
}
