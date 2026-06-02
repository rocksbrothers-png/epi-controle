import 'package:flutter/material.dart';

/// Design tokens mapeados do styles.css (:root CSS variables).
/// Mantém identidade visual do EPI Controle em Flutter.
abstract final class EpiColors {
  // ── Background & Surface ──────────────────────────────────────────────────
  static const background  = Color(0xFFEFE7DB); // --bg
  static const surface     = Color(0xFFFFFAF2); // --panel-strong
  static const surfaceWeak = Color(0xFFFFFCF7); // --panel (sem alpha)

  // ── Text ──────────────────────────────────────────────────────────────────
  static const textPrimary = Color(0xFF1D2A24); // --text
  static const textMuted   = Color(0xFF66726B); // --muted

  // ── Border ────────────────────────────────────────────────────────────────
  static const border      = Color(0x1A1D2A24); // --line (rgba 10%)

  // ── Brand (accent) ────────────────────────────────────────────────────────
  static const brand       = Color(0xFFC85C2C); // --accent
  static const brandDark   = Color(0xFF9B421A); // --accent darker shade
  static const brandSoft   = Color(0xFFF6D8C8); // --accent-soft

  // ── Semantic ──────────────────────────────────────────────────────────────
  static const success     = Color(0xFF226B4C); // --success
  static const successSoft = Color(0xFFD4EDE3);
  static const warning     = Color(0xFFC08822); // --warning
  static const warningSoft = Color(0xFFF9EDCC);
  static const danger      = Color(0xFFA13B2B); // --danger
  static const dangerSoft  = Color(0xFFF9DDD9);
  static const info        = Color(0xFF2B6CB0);
  static const infoSoft    = Color(0xFFD6E4F7);

  // ── Status de EPI ─────────────────────────────────────────────────────────
  static const epiValid    = success;
  static const epiExpiring = warning;
  static const epiExpired  = danger;
  static const epiNoStock  = Color(0xFF5A5A5A);

  // ── Dark mode variants ────────────────────────────────────────────────────
  static const darkBackground = Color(0xFF1A1F1C);
  static const darkSurface    = Color(0xFF242B27);
  static const darkBorder     = Color(0x33E8E0D8); // light-alpha visible on dark bg
}
