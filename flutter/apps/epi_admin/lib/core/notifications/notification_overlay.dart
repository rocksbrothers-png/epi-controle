import 'dart:async';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';

import 'notification_service.dart';

class NotificationOverlay extends StatefulWidget {
  const NotificationOverlay({super.key, required this.child});
  final Widget child;

  @override
  State<NotificationOverlay> createState() => _NotificationOverlayState();
}

class _NotificationOverlayState extends State<NotificationOverlay>
    with SingleTickerProviderStateMixin {
  AppNotification? _current;
  late AnimationController _anim;
  StreamSubscription<AppNotification>? _sub;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _sub = NotificationService().notifications.listen(_onNotification);
  }

  void _onNotification(AppNotification n) {
    setState(() => _current = n);
    _anim.forward(from: 0);
    Future.delayed(const Duration(seconds: 5), _dismiss);
  }

  void _dismiss() {
    _anim.reverse().then((_) {
      if (mounted) setState(() => _current = null);
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _anim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        widget.child,
        if (_current != null)
          Positioned(
            top: MediaQuery.of(context).padding.top + EpiSpacing.sm,
            left: EpiSpacing.lg,
            right: EpiSpacing.lg,
            child: SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0, -1),
                end: Offset.zero,
              ).animate(CurvedAnimation(
                parent: _anim,
                curve: Curves.easeOut,
              )),
              child: Material(
                elevation: 4,
                borderRadius: BorderRadius.circular(EpiRadius.md),
                child: InkWell(
                  onTap: _dismiss,
                  borderRadius: BorderRadius.circular(EpiRadius.md),
                  child: Padding(
                    padding: const EdgeInsets.all(EpiSpacing.md),
                    child: Row(
                      children: [
                        const Icon(Icons.notifications_rounded,
                            color: EpiColors.brand),
                        const SizedBox(width: EpiSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (_current!.title.isNotEmpty)
                                Text(
                                  _current!.title,
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(fontWeight: FontWeight.w700),
                                ),
                              if (_current!.body.isNotEmpty)
                                Text(
                                  _current!.body,
                                  style: Theme.of(context).textTheme.bodySmall,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(width: EpiSpacing.sm),
                        const Icon(Icons.close_rounded,
                            size: 16, color: EpiColors.textMuted),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
