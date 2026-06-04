// Tabela de dados com cabeçalho, linhas zebra, loading e empty state.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

/// Definição de coluna da tabela.
class EpiTableColumn {
  const EpiTableColumn({
    required this.id,
    required this.label,
    this.width,
    this.flex,
    this.align = TextAlign.start,
  });

  final String    id;
  final String    label;
  final double?   width;
  final int?      flex;
  final TextAlign align;
}

class EpiDataTable extends StatelessWidget {
  const EpiDataTable({
    super.key,
    required this.columns,
    required this.rows,
    this.onRowTap,
    this.loading    = false,
    this.emptyLabel = 'Nenhum registro encontrado',
  });

  final List<EpiTableColumn>        columns;
  final List<Map<String, dynamic>>  rows;
  final ValueChanged<Map<String, dynamic>>? onRowTap;
  final bool                        loading;
  final String                      emptyLabel;

  Widget _buildCell(BuildContext context, EpiTableColumn col, dynamic value) {
    final text = value?.toString() ?? '—';
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Text(
        text,
        textAlign: col.align,
        style: Theme.of(context).textTheme.bodySmall,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  Widget _buildHeaderCell(BuildContext context, EpiTableColumn col) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Text(
        col.label,
        textAlign: col.align,
        style: EpiTypography.labelMedium.copyWith(
          fontWeight: FontWeight.w700,
          color: isDark ? const Color(0xFF8A9590) : EpiColors.textMuted,
        ),
      ),
    );
  }

  Widget _cellWrapper(EpiTableColumn col, Widget child) {
    if (col.width != null) {
      return SizedBox(width: col.width, child: child);
    }
    return Expanded(flex: col.flex ?? 1, child: child);
  }

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final headerBg    = isDark ? EpiColors.darkBackground : EpiColors.background;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;
    final surfaceColor = isDark ? EpiColors.darkSurface : EpiColors.surface;

    // Header row
    final header = Container(
      color: headerBg,
      child: Row(
        children: columns.map((c) => _cellWrapper(c, _buildHeaderCell(context, c))).toList(),
      ),
    );

    Widget body;

    if (loading) {
      body = const _SkeletonRows(rowCount: 5);
    } else if (rows.isEmpty) {
      body = Padding(
        padding: const EdgeInsets.all(EpiSpacing.xl3),
        child: Center(
          child: Text(emptyLabel, style: Theme.of(context).textTheme.bodyMedium),
        ),
      );
    } else {
      body = Column(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(rows.length, (i) {
          final row = rows[i];
          final rowBg = i.isOdd
              ? (isDark ? EpiColors.darkBackground.withValues(alpha: 0.5) : EpiColors.background.withValues(alpha:0.5))
              : surfaceColor;
          return GestureDetector(
            onTap: onRowTap != null ? () => onRowTap!(row) : null,
            child: Container(
              color: rowBg,
              child: Row(
                children: columns
                    .map((c) => _cellWrapper(c, _buildCell(context, c, row[c.id])))
                    .toList(),
              ),
            ),
          );
        }),
      );
    }

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: borderColor),
        borderRadius: BorderRadius.circular(EpiRadius.md),
        color: surfaceColor,
      ),
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 400),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              header,
              Divider(height: 1, thickness: 1, color: borderColor),
              body,
            ],
          ),
        ),
      ),
    );
  }
}

class _SkeletonRows extends StatefulWidget {
  const _SkeletonRows({this.rowCount = 5});
  final int rowCount;

  @override
  State<_SkeletonRows> createState() => _SkeletonRowsState();
}

class _SkeletonRowsState extends State<_SkeletonRows>
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
    _anim = Tween<double>(begin: 0.3, end: 0.7).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Column(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(widget.rowCount, (i) {
          return Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.lg,
              vertical: EpiSpacing.md,
            ),
            child: Container(
              height: 14,
              decoration: BoxDecoration(
                color: Color.lerp(
                  EpiColors.background,
                  EpiColors.border,
                  _anim.value,
                ),
                borderRadius: BorderRadius.circular(EpiRadius.xs),
              ),
            ),
          );
        }),
      ),
    );
  }
}
