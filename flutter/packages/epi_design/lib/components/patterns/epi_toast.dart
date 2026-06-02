// Toast/Snackbar padronizado com ícone por tipo e auto-dismiss.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

enum EpiToastType { success, error, warning, info }

/// Exibe um toast padronizado do Design System EPI Controle.
void showEpiToast(
  BuildContext context, {
  required String  message,
  EpiToastType     type     = EpiToastType.info,
  Duration         duration = const Duration(seconds: 3),
}) {
  final (bg, icon) = switch (type) {
    EpiToastType.success => (EpiColors.success, Icons.check_circle_rounded),
    EpiToastType.error   => (EpiColors.danger,  Icons.error_rounded),
    EpiToastType.warning => (EpiColors.warning, Icons.warning_rounded),
    EpiToastType.info    => (EpiColors.info,    Icons.info_rounded),
  };

  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
        SnackBar(
          duration: duration,
          behavior: SnackBarBehavior.floating,
          dismissDirection: DismissDirection.horizontal,
          margin: const EdgeInsets.all(EpiSpacing.lg),
          padding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
            vertical: EpiSpacing.md,
          ),
          backgroundColor: bg,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(EpiRadius.md),
          ),
          content: Row(
            children: [
              Icon(icon, color: Colors.white, size: 20),
              const SizedBox(width: EpiSpacing.sm),
              Expanded(
                child: Text(
                  message,
                  style: EpiTypography.bodyMedium.copyWith(color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      );
}
