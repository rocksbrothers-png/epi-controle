// Timeline vertical de eventos com linha conectora e ponto colorido por evento.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

/// Evento individual da EpiTimeline.
class EpiTimelineEvent {
  const EpiTimelineEvent({
    required this.title,
    this.subtitle,
    required this.timestamp,
    this.icon,
    this.color,
    this.body,
  });

  final String    title;
  final String?   subtitle;
  final DateTime  timestamp;
  final IconData? icon;
  final Color?    color;
  final Widget?   body;
}

class EpiTimeline extends StatelessWidget {
  const EpiTimeline({
    super.key,
    required this.events,
    this.shrinkWrap = false,
  });

  final List<EpiTimelineEvent> events;
  final bool                   shrinkWrap;

  String _formatDateTime(DateTime dt) {
    final d  = dt.day.toString().padLeft(2, '0');
    final mo = dt.month.toString().padLeft(2, '0');
    final y  = dt.year;
    final h  = dt.hour.toString().padLeft(2, '0');
    final mi = dt.minute.toString().padLeft(2, '0');
    return '$d/$mo/$y $h:$mi';
  }

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) return const SizedBox.shrink();

    return ListView.builder(
      shrinkWrap: shrinkWrap,
      physics: shrinkWrap ? const NeverScrollableScrollPhysics() : null,
      itemCount: events.length,
      itemBuilder: (context, i) {
        final event    = events[i];
        final isLast   = i == events.length - 1;
        final isDark   = Theme.of(context).brightness == Brightness.dark;
        final dotColor = event.color ?? EpiColors.brand;
        final lineColor = isDark ? EpiColors.darkBorder : EpiColors.border;
        final mutedColor = isDark ? const Color(0xFF8A9590) : EpiColors.textMuted;

        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Timeline column: dot + line
              SizedBox(
                width: 32,
                child: Column(
                  children: [
                    // Dot / icon
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: dotColor.withOpacity(0.15),
                        shape: BoxShape.circle,
                        border: Border.all(color: dotColor, width: 2),
                      ),
                      alignment: Alignment.center,
                      child: event.icon != null
                          ? Icon(event.icon, size: 14, color: dotColor)
                          : Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: dotColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                    ),
                    // Connector line
                    if (!isLast)
                      Expanded(
                        child: Container(
                          width: 2,
                          margin: const EdgeInsets.symmetric(vertical: EpiSpacing.xs),
                          color: lineColor,
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: EpiSpacing.md),
              // Content
              Expanded(
                child: Padding(
                  padding: EdgeInsets.only(
                    bottom: isLast ? 0 : EpiSpacing.xl,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: EpiSpacing.xs),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              event.title,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          Text(
                            _formatDateTime(event.timestamp),
                            style: EpiTypography.labelSmall.copyWith(
                              color: mutedColor,
                            ),
                          ),
                        ],
                      ),
                      if (event.subtitle != null) ...[
                        const SizedBox(height: EpiSpacing.xs),
                        Text(
                          event.subtitle!,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall!
                              .copyWith(color: mutedColor),
                        ),
                      ],
                      if (event.body != null) ...[
                        const SizedBox(height: EpiSpacing.sm),
                        event.body!,
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
