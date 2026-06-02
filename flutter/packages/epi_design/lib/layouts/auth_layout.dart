/// Layout centralizado para telas de autenticação com card e logo.
import 'package:flutter/material.dart';
import '../tokens/colors.dart';
import '../tokens/spacing.dart';
import '../tokens/typography.dart';

class AuthLayout extends StatelessWidget {
  const AuthLayout({
    super.key,
    required this.child,
    this.title,
    this.subtitle,
    this.logo,
  });

  final Widget  child;
  final String? title;
  final String? subtitle;
  final Widget? logo;

  @override
  Widget build(BuildContext context) {
    final isDark       = Theme.of(context).brightness == Brightness.dark;
    final bgColor      = isDark ? EpiColors.darkBackground : EpiColors.background;
    final cardColor    = isDark ? EpiColors.darkSurface    : EpiColors.surface;
    final borderColor  = isDark ? EpiColors.darkBorder     : EpiColors.border;
    final textColor    = isDark ? const Color(0xFFE8E0D8)  : EpiColors.textPrimary;
    final mutedColor   = isDark ? const Color(0xFF8A9590)  : EpiColors.textMuted;

    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(EpiSpacing.xl2),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Logo
                  logo ??
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.security_rounded,
                            color: EpiColors.brand,
                            size: 32,
                          ),
                          const SizedBox(width: EpiSpacing.sm),
                          Text(
                            'EPI Controle',
                            style: EpiTypography.headlineLarge.copyWith(
                              color: EpiColors.brand,
                            ),
                          ),
                        ],
                      ),
                  const SizedBox(height: EpiSpacing.xl2),
                  // Card
                  Container(
                    padding: const EdgeInsets.all(EpiSpacing.xl2),
                    decoration: BoxDecoration(
                      color: cardColor,
                      borderRadius: BorderRadius.circular(EpiRadius.xl),
                      border: Border.all(color: borderColor),
                      boxShadow: isDark
                          ? null
                          : [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.08),
                                blurRadius: 24,
                                offset: const Offset(0, 8),
                              ),
                            ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (title != null) ...[
                          Text(
                            title!,
                            style: EpiTypography.headlineMedium.copyWith(
                              color: textColor,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: EpiSpacing.xs),
                        ],
                        if (subtitle != null) ...[
                          Text(
                            subtitle!,
                            style: EpiTypography.bodyMedium.copyWith(
                              color: mutedColor,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: EpiSpacing.xl2),
                        ],
                        child,
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
