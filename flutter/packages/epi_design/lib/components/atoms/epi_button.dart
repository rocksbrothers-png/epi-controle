import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

enum EpiButtonVariant { primary, ghost, danger, success }
enum EpiButtonSize    { sm, md, lg }

class EpiButton extends StatelessWidget {
  const EpiButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant  = EpiButtonVariant.primary,
    this.size     = EpiButtonSize.md,
    this.icon,
    this.loading  = false,
    this.fullWidth= false,
  });

  final String           label;
  final VoidCallback?    onPressed;
  final EpiButtonVariant variant;
  final EpiButtonSize    size;
  final IconData?        icon;
  final bool             loading;
  final bool             fullWidth;

  @override
  Widget build(BuildContext context) {
    final (bg, fg, border) = switch (variant) {
      EpiButtonVariant.primary => (EpiColors.brand,    Colors.white,          EpiColors.brand),
      EpiButtonVariant.ghost   => (Colors.transparent, EpiColors.brand,       EpiColors.brand),
      EpiButtonVariant.danger  => (EpiColors.danger,   Colors.white,          EpiColors.danger),
      EpiButtonVariant.success => (EpiColors.success,  Colors.white,          EpiColors.success),
    };

    final (h, hPad, textStyle) = switch (size) {
      EpiButtonSize.sm => (36.0, EpiSpacing.lg,  Theme.of(context).textTheme.labelMedium!),
      EpiButtonSize.md => (44.0, EpiSpacing.xl2, Theme.of(context).textTheme.labelLarge!),
      EpiButtonSize.lg => (52.0, EpiSpacing.xl3, Theme.of(context).textTheme.titleMedium!),
    };

    final Widget child = loading
        ? SizedBox(
            width: 18, height: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: fg),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[Icon(icon, size: 18, color: fg), const SizedBox(width: 6)],
              Text(label, style: textStyle.copyWith(color: fg)),
            ],
          );

    final button = SizedBox(
      height: h,
      child: OutlinedButton(
        onPressed: loading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          backgroundColor: bg,
          foregroundColor: fg,
          side: BorderSide(color: border),
          padding: EdgeInsets.symmetric(horizontal: hPad),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: child,
      ),
    );

    return fullWidth ? SizedBox(width: double.infinity, child: button) : button;
  }
}
