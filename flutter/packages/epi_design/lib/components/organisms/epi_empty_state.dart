import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../atoms/epi_button.dart';

class EpiEmptyState extends StatelessWidget {
  const EpiEmptyState({
    super.key,
    required this.title,
    this.subtitle,
    this.icon       = Icons.inbox_outlined,
    this.ctaLabel,
    this.onCtaPressed,
  });

  final String        title;
  final String?       subtitle;
  final IconData      icon;
  final String?       ctaLabel;
  final VoidCallback? onCtaPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.xl3),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(EpiSpacing.xl2),
              decoration: BoxDecoration(
                color: EpiColors.brand.withValues(alpha:
                  Theme.of(context).brightness == Brightness.dark ? 0.15 : 0.12,
                ),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 48, color: EpiColors.brand),
            ),
            const SizedBox(height: EpiSpacing.xl),
            Text(title, style: theme.textTheme.headlineSmall, textAlign: TextAlign.center),
            if (subtitle != null) ...[
              const SizedBox(height: EpiSpacing.sm),
              Text(subtitle!, style: theme.textTheme.bodyMedium, textAlign: TextAlign.center),
            ],
            if (ctaLabel != null && onCtaPressed != null) ...[
              const SizedBox(height: EpiSpacing.xl2),
              EpiButton(label: ctaLabel!, onPressed: onCtaPressed),
            ],
          ],
        ),
      ),
    );
  }
}
