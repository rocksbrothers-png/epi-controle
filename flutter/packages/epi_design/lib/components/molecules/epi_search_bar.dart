// Barra de busca com debounce e botão de limpar do Design System EPI Controle.
import 'dart:async';
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

class EpiSearchBar extends StatefulWidget {
  const EpiSearchBar({
    super.key,
    this.hint          = 'Buscar…',
    this.onChanged,
    this.onClear,
    this.controller,
    this.debounceMs    = 300,
  });

  final String?              hint;
  final ValueChanged<String>? onChanged;
  final VoidCallback?        onClear;
  final TextEditingController? controller;
  final int                  debounceMs;

  @override
  State<EpiSearchBar> createState() => _EpiSearchBarState();
}

class _EpiSearchBarState extends State<EpiSearchBar> {
  late final TextEditingController _ctrl;
  Timer?   _debounce;
  bool     _hasText = false;

  @override
  void initState() {
    super.initState();
    _ctrl = widget.controller ?? TextEditingController();
    _hasText = _ctrl.text.isNotEmpty;
    _ctrl.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final hasText = _ctrl.text.isNotEmpty;
    if (hasText != _hasText) setState(() => _hasText = hasText);

    _debounce?.cancel();
    _debounce = Timer(Duration(milliseconds: widget.debounceMs), () {
      widget.onChanged?.call(_ctrl.text);
    });
  }

  void _clear() {
    _ctrl.clear();
    widget.onChanged?.call('');
    widget.onClear?.call();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    if (widget.controller == null) _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark       = Theme.of(context).brightness == Brightness.dark;
    final borderColor  = isDark ? EpiColors.darkBorder : EpiColors.border;
    final fillColor    = isDark ? EpiColors.darkSurface : EpiColors.surface;

    return SizedBox(
      height: 44,
      child: TextField(
        controller: _ctrl,
        style: Theme.of(context).textTheme.bodyMedium,
        decoration: InputDecoration(
          hintText: widget.hint,
          filled: true,
          fillColor: fillColor,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
            vertical: 0,
          ),
          prefixIcon: const Padding(
            padding: EdgeInsets.symmetric(horizontal: EpiSpacing.md),
            child: Icon(Icons.search_rounded, size: 20, color: EpiColors.textMuted),
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 44, minHeight: 44),
          suffixIcon: _hasText
              ? IconButton(
                  icon: const Icon(Icons.close_rounded, size: 18),
                  color: EpiColors.textMuted,
                  onPressed: _clear,
                  splashRadius: 16,
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(EpiRadius.md),
            borderSide: BorderSide(color: borderColor),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(EpiRadius.md),
            borderSide: BorderSide(color: borderColor),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(EpiRadius.md),
            borderSide: const BorderSide(color: EpiColors.brand, width: 1.5),
          ),
        ),
      ),
    );
  }
}
