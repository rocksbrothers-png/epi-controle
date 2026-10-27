import 'package:dio/dio.dart';

/// Reads the effective device locale for each request, including refresh/retry.
/// Presentation only: no locale, identity or tenant field enters the payload.
class LocaleHeaderInterceptor extends Interceptor {
  LocaleHeaderInterceptor(this.localeTag);
  final String? Function() localeTag;
  static const supported = {'pt-BR', 'en-US', 'es-ES', 'fr-FR', 'no-NO'};

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final tag = localeTag();
    if (supported.contains(tag)) {
      for (final key
          in options.headers.keys
              .where((key) => key.toLowerCase() == 'accept-language')
              .toList()) {
        options.headers.remove(key);
      }
      options.headers['Accept-Language'] = tag;
    }
    handler.next(options);
  }
}
