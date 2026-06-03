import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

/// Handles FCM setup and in-app notification routing.
/// Requires firebase_options.dart to be configured before use.
class NotificationService {
  static final NotificationService _instance = NotificationService._();
  factory NotificationService() => _instance;
  NotificationService._();

  final _controller = StreamController<AppNotification>.broadcast();
  Stream<AppNotification> get notifications => _controller.stream;

  /// Set to true from main.dart after Firebase.initializeApp() succeeds.
  static bool firebaseAvailable = false;

  /// Call after Firebase.initializeApp(). Safe to call even if Firebase
  /// isn't configured — will silently no-op if Firebase isn't available.
  Future<void> init() async {
    if (!firebaseAvailable) return;
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      // Foreground messages
      FirebaseMessaging.onMessage.listen(_handleMessage);

      // Notification taps when app was in background
      FirebaseMessaging.onMessageOpenedApp.listen(_handleMessage);

      // Initial message if app was terminated
      final initial = await messaging.getInitialMessage();
      if (initial != null) _handleMessage(initial);
    } on Exception {
      // Firebase not configured — silently ignore
    }
  }

  void _handleMessage(RemoteMessage message) {
    _controller.add(AppNotification(
      title: message.notification?.title ?? '',
      body: message.notification?.body ?? '',
      data: message.data,
    ));
  }

  /// Push a local notification directly into the stream (e.g. critical-stock alerts).
  void simulateNotification(AppNotification notification) {
    _controller.add(notification);
  }

  void dispose() {
    _controller.close();
  }
}

class AppNotification {
  const AppNotification({
    required this.title,
    required this.body,
    required this.data,
  });
  final String title;
  final String body;
  final Map<String, dynamic> data;
}
