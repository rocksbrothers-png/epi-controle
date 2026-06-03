import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

/// Firebase options populated at build time via --dart-define.
///
/// Required defines:
///   FIREBASE_PROJECT_ID, FIREBASE_SENDER_ID, FIREBASE_STORAGE_BUCKET
///   FIREBASE_ANDROID_API_KEY, FIREBASE_ANDROID_APP_ID
///   FIREBASE_WEB_API_KEY,     FIREBASE_WEB_APP_ID
///   FIREBASE_IOS_API_KEY,     FIREBASE_IOS_APP_ID
///
/// When any define is absent (e.g. in dev CI) initializeApp() throws
/// StateError, which main.dart catches — app runs without push notifications.
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError(
          'Firebase is not configured for ${defaultTargetPlatform.name}.',
        );
    }
  }

  static const _projectId =
      String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const _senderId =
      String.fromEnvironment('FIREBASE_SENDER_ID');
  static const _bucket =
      String.fromEnvironment('FIREBASE_STORAGE_BUCKET');

  static FirebaseOptions get web => _checked(const FirebaseOptions(
        apiKey: String.fromEnvironment('FIREBASE_WEB_API_KEY'),
        appId: String.fromEnvironment('FIREBASE_WEB_APP_ID'),
        messagingSenderId: _senderId,
        projectId: _projectId,
        storageBucket: _bucket,
        authDomain: '$_projectId.firebaseapp.com',
      ));

  static FirebaseOptions get android => _checked(const FirebaseOptions(
        apiKey: String.fromEnvironment('FIREBASE_ANDROID_API_KEY'),
        appId: String.fromEnvironment('FIREBASE_ANDROID_APP_ID'),
        messagingSenderId: _senderId,
        projectId: _projectId,
        storageBucket: _bucket,
      ));

  static FirebaseOptions get ios => _checked(const FirebaseOptions(
        apiKey: String.fromEnvironment('FIREBASE_IOS_API_KEY'),
        appId: String.fromEnvironment('FIREBASE_IOS_APP_ID'),
        messagingSenderId: _senderId,
        projectId: _projectId,
        storageBucket: _bucket,
        iosBundleId: 'com.rocksbrothers.epicontrole',
      ));

  static FirebaseOptions _checked(FirebaseOptions opts) {
    if (opts.projectId.isEmpty) {
      throw StateError(
        'Firebase não configurado — defina FIREBASE_PROJECT_ID via --dart-define.',
      );
    }
    return opts;
  }
}
