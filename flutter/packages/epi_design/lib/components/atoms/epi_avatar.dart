import 'package:flutter/material.dart';
import '../../tokens/colors.dart';

/// Avatar com iniciais e cor determinística baseada no nome.
/// Sem foto agora — câmera adicionada na Fase UX-2.
class EpiAvatar extends StatelessWidget {
  const EpiAvatar({super.key, required this.name, this.size = 40, this.imageUrl});

  final String  name;
  final double  size;
  final String? imageUrl;

  static Color _colorForName(String name) {
    const palette = [
      Color(0xFFC85C2C), Color(0xFF226B4C), Color(0xFF2B6CB0),
      Color(0xFF744210), Color(0xFF6B21A8), Color(0xFF065F46),
      Color(0xFF991B1B), Color(0xFF1E40AF),
    ];
    final hash = name.codeUnits.fold(0, (acc, c) => acc + c);
    return palette[hash % palette.length];
  }

  String get _initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    if (parts.first.isNotEmpty) return parts.first.substring(0, parts.first.length.clamp(0, 2)).toUpperCase();
    return '?';
  }

  @override
  Widget build(BuildContext context) {
    if (imageUrl != null) {
      return ClipOval(
        child: Image.network(imageUrl!, width: size, height: size, fit: BoxFit.cover),
      );
    }
    final color = _colorForName(name);
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      alignment: Alignment.center,
      child: Text(
        _initials,
        style: TextStyle(
          color: Colors.white,
          fontSize: size * 0.38,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
