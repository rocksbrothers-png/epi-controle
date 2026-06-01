import 'package:flutter/material.dart';

abstract final class EpiTypography {
  // Inter substituindo Segoe UI — web font consistente cross-platform
  static const fontFamily = 'Inter';
  static const fontFamilyFallback = ['Segoe UI', 'Arial', 'sans-serif'];

  static const displayLarge  = TextStyle(fontSize: 32, fontWeight: FontWeight.w700, letterSpacing: -0.5);
  static const displayMedium = TextStyle(fontSize: 26, fontWeight: FontWeight.w700, letterSpacing: -0.3);
  static const headlineLarge = TextStyle(fontSize: 22, fontWeight: FontWeight.w600, letterSpacing: -0.2);
  static const headlineMedium= TextStyle(fontSize: 18, fontWeight: FontWeight.w600);
  static const headlineSmall = TextStyle(fontSize: 16, fontWeight: FontWeight.w600);
  static const titleLarge    = TextStyle(fontSize: 15, fontWeight: FontWeight.w600);
  static const titleMedium   = TextStyle(fontSize: 14, fontWeight: FontWeight.w600);
  static const bodyLarge     = TextStyle(fontSize: 15, fontWeight: FontWeight.w400);
  static const bodyMedium    = TextStyle(fontSize: 14, fontWeight: FontWeight.w400);
  static const bodySmall     = TextStyle(fontSize: 13, fontWeight: FontWeight.w400);
  static const labelLarge    = TextStyle(fontSize: 14, fontWeight: FontWeight.w500);
  static const labelMedium   = TextStyle(fontSize: 12, fontWeight: FontWeight.w500, letterSpacing: 0.5);
  static const labelSmall    = TextStyle(fontSize: 11, fontWeight: FontWeight.w500, letterSpacing: 0.5);
}
