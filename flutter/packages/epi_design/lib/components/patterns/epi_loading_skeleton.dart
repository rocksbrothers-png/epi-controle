/// Skeleton de carregamento com animação shimmer para vários contextos.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';

class EpiLoadingSkeleton extends StatefulWidget {
  const EpiLoadingSkeleton({
    super.key,
    this.width,
    this.height    = 16,
    this.borderRadius,
    this.lines     = 1,
  });

  final double?  width;
  final double   height;
  final double?  borderRadius;
  final int      lines;

  @override
  State<EpiLoadingSkeleton> createState() => _EpiLoadingSkeletonState();
}

class _EpiLoadingSkeletonState extends State<EpiLoadingSkeleton>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double>   _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.0, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    final base     = isDark ? EpiColors.darkBorder : EpiColors.border;
    final shimmer  = isDark
        ? const Color(0xFF3A4540)
        : EpiColors.background;

    final radius = widget.borderRadius ?? EpiRadius.sm;

    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        final color = Color.lerp(base, shimmer, _anim.value);
        if (widget.lines <= 1) {
          return Container(
            width:  widget.width,
            height: widget.height,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(radius),
            ),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: List.generate(widget.lines, (i) {
            final lineWidth = (i == widget.lines - 1 && widget.lines > 1)
                ? (widget.width != null ? widget.width! * 0.7 : null)
                : widget.width;
            return Padding(
              padding: EdgeInsets.only(
                bottom: i < widget.lines - 1 ? EpiSpacing.sm : 0,
              ),
              child: Container(
                width: lineWidth,
                height: widget.height,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(radius),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

/// Card skeleton: header icon + title + várias linhas de conteúdo.
class EpiSkeletonCard extends StatelessWidget {
  const EpiSkeletonCard({super.key, this.lines = 3});
  final int lines;

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final bgColor     = isDark ? EpiColors.darkSurface : EpiColors.surface;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;

    return Container(
      padding: const EdgeInsets.all(EpiSpacing.lg),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(EpiRadius.lg),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const EpiLoadingSkeleton(width: 36, height: 36, borderRadius: EpiRadius.sm),
              const SizedBox(width: EpiSpacing.md),
              Expanded(
                child: EpiLoadingSkeleton(
                  height: 14,
                  width: double.infinity,
                  borderRadius: EpiRadius.xs,
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.lg),
          EpiLoadingSkeleton(
            height: 28,
            lines: lines,
            width: double.infinity,
          ),
        ],
      ),
    );
  }
}

/// Table skeleton: N linhas de largura variável simulando rows de tabela.
class EpiSkeletonTable extends StatelessWidget {
  const EpiSkeletonTable({super.key, this.rowCount = 5, this.columns = 4});
  final int rowCount;
  final int columns;

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final bgColor     = isDark ? EpiColors.darkSurface : EpiColors.surface;
    final headerBg    = isDark ? EpiColors.darkBackground : EpiColors.background;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(EpiRadius.md),
        border: Border.all(color: borderColor),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Container(
            color: headerBg,
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.lg,
              vertical: EpiSpacing.md,
            ),
            child: Row(
              children: List.generate(columns, (i) => Expanded(
                child: Padding(
                  padding: EdgeInsets.only(right: i < columns - 1 ? EpiSpacing.lg : 0),
                  child: const EpiLoadingSkeleton(height: 12),
                ),
              )),
            ),
          ),
          Divider(height: 1, thickness: 1, color: borderColor),
          // Rows
          ...List.generate(rowCount, (i) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: EpiSpacing.lg,
                  vertical: EpiSpacing.md,
                ),
                child: Row(
                  children: List.generate(columns, (j) => Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(right: j < columns - 1 ? EpiSpacing.lg : 0),
                      child: EpiLoadingSkeleton(
                        height: 12,
                        width: j == 0 ? 80 : null,
                      ),
                    ),
                  )),
                ),
              ),
              if (i < rowCount - 1) Divider(height: 1, thickness: 1, color: borderColor),
            ],
          )),
        ],
      ),
    );
  }
}
