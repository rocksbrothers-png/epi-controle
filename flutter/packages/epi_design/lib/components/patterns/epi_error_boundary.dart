// Widget de estado de erro com ícone, mensagem e botão de retry.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../atoms/epi_button.dart';

class EpiErrorState extends StatelessWidget {
  const EpiErrorState({
    super.key,
    required this.message,
    this.onRetry,
    this.icon = Icons.error_outline_rounded,
  });

  final String        message;
  final VoidCallback? onRetry;
  final IconData      icon;

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
                color: EpiColors.danger.withValues(alpha:
                  Theme.of(context).brightness == Brightness.dark ? 0.15 : 0.12,
                ),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 48, color: EpiColors.danger),
            ),
            const SizedBox(height: EpiSpacing.xl),
            Text(
              'Ocorreu um erro',
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              message,
              style: theme.textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: EpiSpacing.xl2),
              EpiButton(
                label: 'Tentar novamente',
                onPressed: onRetry,
                icon: Icons.refresh_rounded,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
