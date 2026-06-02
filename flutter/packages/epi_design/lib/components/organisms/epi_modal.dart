// Modal padronizado com header, body scrollável e footer de ações.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

/// Exibe um modal padronizado do Design System EPI Controle.
Future<T?> showEpiModal<T>(
  BuildContext context, {
  String?       title,
  Widget?       body,
  List<Widget>? actions,
  double        width = 480,
  bool          barrierDismissible = true,
}) {
  return showDialog<T>(
    context: context,
    barrierDismissible: barrierDismissible,
    builder: (_) => _EpiModalDialog(
      title:   title,
      body:    body,
      actions: actions,
      width:   width,
    ),
  );
}

class _EpiModalDialog extends StatelessWidget {
  const _EpiModalDialog({
    this.title,
    this.body,
    this.actions,
    required this.width,
  });

  final String?       title;
  final Widget?       body;
  final List<Widget>? actions;
  final double        width;

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final bgColor     = isDark ? EpiColors.darkSurface : EpiColors.surface;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;

    return Dialog(
      backgroundColor: bgColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(EpiRadius.xl),
        side: BorderSide(color: borderColor),
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: width, maxHeight: 600),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(
                EpiSpacing.xl2, EpiSpacing.xl, EpiSpacing.md, EpiSpacing.lg,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: title != null
                        ? Text(
                            title!,
                            style: Theme.of(context).textTheme.headlineSmall,
                          )
                        : const SizedBox.shrink(),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                    splashRadius: 20,
                    color: EpiColors.textMuted,
                  ),
                ],
              ),
            ),
            Divider(height: 1, thickness: 1, color: borderColor),
            // Body
            if (body != null)
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(EpiSpacing.xl2),
                  child: body!,
                ),
              ),
            // Footer
            if (actions != null && actions!.isNotEmpty) ...[
              Divider(height: 1, thickness: 1, color: borderColor),
              Padding(
                padding: const EdgeInsets.all(EpiSpacing.lg),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: actions!
                      .expand((w) => [w, const SizedBox(width: EpiSpacing.sm)])
                      .toList()
                    ..removeLast(),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
