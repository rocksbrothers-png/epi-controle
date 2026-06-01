import 'package:flutter/material.dart';
import '../tokens/colors.dart';
import '../tokens/spacing.dart';
import '../tokens/typography.dart';

abstract final class EpiTheme {
  static ThemeData get light => _build(brightness: Brightness.light);
  static ThemeData get dark  => _build(brightness: Brightness.dark);

  static ThemeData _build({required Brightness brightness}) {
    final isDark = brightness == Brightness.dark;
    final bg      = isDark ? EpiColors.darkBackground : EpiColors.background;
    final surface = isDark ? EpiColors.darkSurface    : EpiColors.surface;
    final text    = isDark ? const Color(0xFFE8E0D8)  : EpiColors.textPrimary;
    final muted   = isDark ? const Color(0xFF8A9590)  : EpiColors.textMuted;

    final colorScheme = ColorScheme(
      brightness:       brightness,
      primary:          EpiColors.brand,
      onPrimary:        Colors.white,
      primaryContainer: EpiColors.brandSoft,
      onPrimaryContainer: EpiColors.brand,
      secondary:        EpiColors.success,
      onSecondary:      Colors.white,
      error:            EpiColors.danger,
      onError:          Colors.white,
      surface:          surface,
      onSurface:        text,
      surfaceContainerHighest: isDark ? EpiColors.darkBorder : EpiColors.border,
      outline:          muted,
    );

    return ThemeData(
      useMaterial3:  true,
      colorScheme:   colorScheme,
      scaffoldBackgroundColor: bg,
      fontFamily:    EpiTypography.fontFamily,
      textTheme: TextTheme(
        displayLarge:  EpiTypography.displayLarge.copyWith(color: text),
        displayMedium: EpiTypography.displayMedium.copyWith(color: text),
        headlineLarge: EpiTypography.headlineLarge.copyWith(color: text),
        headlineMedium:EpiTypography.headlineMedium.copyWith(color: text),
        headlineSmall: EpiTypography.headlineSmall.copyWith(color: text),
        titleLarge:    EpiTypography.titleLarge.copyWith(color: text),
        titleMedium:   EpiTypography.titleMedium.copyWith(color: text),
        bodyLarge:     EpiTypography.bodyLarge.copyWith(color: text),
        bodyMedium:    EpiTypography.bodyMedium.copyWith(color: text),
        bodySmall:     EpiTypography.bodySmall.copyWith(color: muted),
        labelLarge:    EpiTypography.labelLarge.copyWith(color: text),
        labelMedium:   EpiTypography.labelMedium.copyWith(color: muted),
        labelSmall:    EpiTypography.labelSmall.copyWith(color: muted),
      ),
      cardTheme: CardThemeData(
        color:       surface,
        elevation:   0,
        shape:       RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EpiRadius.md),
          side: BorderSide(color: EpiColors.border, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled:      true,
        fillColor:   surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: EpiSpacing.lg, vertical: EpiSpacing.md,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EpiRadius.sm),
          borderSide:   BorderSide(color: EpiColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EpiRadius.sm),
          borderSide:   BorderSide(color: EpiColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EpiRadius.sm),
          borderSide:   BorderSide(color: EpiColors.brand, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EpiRadius.sm),
          borderSide:   BorderSide(color: EpiColors.danger),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: EpiColors.brand,
          foregroundColor: Colors.white,
          minimumSize: const Size(88, 44),
          padding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.xl2, vertical: EpiSpacing.md,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(EpiRadius.sm),
          ),
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: EpiColors.brand,
          minimumSize: const Size(88, 44),
          padding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.xl2, vertical: EpiSpacing.md,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(EpiRadius.sm),
          ),
          side: const BorderSide(color: EpiColors.brand),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: EpiColors.border,
        thickness: 1,
        space: 0,
      ),
    );
  }
}
