// Linha de status com dot colorido, label e timestamp formatado.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../atoms/epi_badge.dart';

class EpiStatusRow extends StatelessWidget {
  const EpiStatusRow({
    super.key,
    required this.label,
    required this.status,
    this.timestamp,
    this.subtitle,
  });

  final String          label;
  final EpiBadgeStatus  status;
  final DateTime?       timestamp;
  final String?         subtitle;

  static Color _dotColor(EpiBadgeStatus s) => switch (s) {
    EpiBadgeStatus.active   => EpiColors.success,
    EpiBadgeStatus.inactive => EpiColors.textMuted,
    EpiBadgeStatus.expired  => EpiColors.danger,
    EpiBadgeStatus.expiring => EpiColors.warning,
    EpiBadgeStatus.pending  => EpiColors.warning,
    EpiBadgeStatus.approved => EpiColors.success,
    EpiBadgeStatus.rejected => EpiColors.danger,
    EpiBadgeStatus.inReview => EpiColors.info,
    EpiBadgeStatus.noStock  => EpiColors.textMuted,
    EpiBadgeStatus.critical => EpiColors.danger,
  };

  String _formatDate(DateTime dt) {
    final d = dt.day.toString().padLeft(2, '0');
    final m = dt.month.toString().padLeft(2, '0');
    final y = dt.year;
    return '$d/$m/$y';
  }

  @override
  Widget build(BuildContext context) {
    final isDark    = Theme.of(context).brightness == Brightness.dark;
    final mutedColor = isDark ? const Color(0xFF8A9590) : EpiColors.textMuted;
    final dotColor  = _dotColor(status);

    return Row(
      children: [
        // Status dot
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
        ),
        const SizedBox(width: EpiSpacing.sm),
        // Label + subtitle
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.bodyMedium,
                overflow: TextOverflow.ellipsis,
              ),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: Theme.of(context)
                      .textTheme
                      .labelMedium!
                      .copyWith(color: mutedColor),
                  overflow: TextOverflow.ellipsis,
                ),
            ],
          ),
        ),
        if (timestamp != null) ...[
          const SizedBox(width: EpiSpacing.sm),
          Text(
            _formatDate(timestamp!),
            style: Theme.of(context)
                .textTheme
                .labelMedium!
                .copyWith(color: mutedColor),
          ),
        ],
      ],
    );
  }
}
