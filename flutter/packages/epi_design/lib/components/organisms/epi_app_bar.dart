// AppBar padronizada com suporte a breadcrumb e altura fixa de 60px.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

class EpiAppBar extends StatelessWidget implements PreferredSizeWidget {
  const EpiAppBar({
    super.key,
    required this.title,
    this.leading,
    this.actions,
    this.showBreadcrumb = false,
    this.breadcrumbs    = const [],
  });

  final String        title;
  final Widget?       leading;
  final List<Widget>? actions;
  final bool          showBreadcrumb;
  final List<String>  breadcrumbs;

  static const double _height = 60;

  @override
  Size get preferredSize => const Size.fromHeight(_height);

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final bgColor     = isDark ? EpiColors.darkSurface : EpiColors.surface;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;
    final textColor   = isDark ? const Color(0xFFE8E0D8) : EpiColors.textPrimary;
    final mutedColor  = isDark ? const Color(0xFF8A9590) : EpiColors.textMuted;

    Widget? titleWidget;
    if (showBreadcrumb && breadcrumbs.isNotEmpty) {
      titleWidget = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(title, style: EpiTypography.headlineSmall.copyWith(color: textColor)),
          const SizedBox(height: 2),
          _Breadcrumb(breadcrumbs: breadcrumbs, mutedColor: mutedColor),
        ],
      );
    } else {
      titleWidget = Text(
        title,
        style: EpiTypography.headlineSmall.copyWith(color: textColor),
      );
    }

    return Container(
      height: _height,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(bottom: BorderSide(color: borderColor)),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
          child: Row(
            children: [
              if (leading != null) ...[leading!, const SizedBox(width: EpiSpacing.sm)],
              Expanded(child: titleWidget),
              if (actions != null)
                ...actions!.expand((w) => [w, const SizedBox(width: EpiSpacing.xs)]).toList()
                  ..removeLast(),
            ],
          ),
        ),
      ),
    );
  }
}

class _Breadcrumb extends StatelessWidget {
  const _Breadcrumb({required this.breadcrumbs, required this.mutedColor});
  final List<String> breadcrumbs;
  final Color        mutedColor;

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[];
    for (var i = 0; i < breadcrumbs.length; i++) {
      if (i > 0) {
        items.add(
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.xs),
            child: Icon(Icons.chevron_right_rounded, size: 14, color: mutedColor),
          ),
        );
      }
      items.add(
        Text(
          breadcrumbs[i],
          style: EpiTypography.labelSmall.copyWith(color: mutedColor),
        ),
      );
    }
    return Row(children: items);
  }
}
