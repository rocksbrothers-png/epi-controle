import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:local_auth/local_auth.dart';
import '../api/api_client.dart';
import 'auth_state.dart';

class AuthCubit extends Cubit<AuthState> {
  AuthCubit() : super(const AuthInitial());

  Future<void> tryAutoLogin() async {
    final token = await ApiClient.getToken();
    if (token != null) {
      emit(AuthAuthenticated(token: token, user: const {}));
    }
  }

  Future<void> login({
    required String username,
    required String password,
  }) async {
    if (username.isEmpty || password.isEmpty) {
      emit(const AuthError('empty'));
      return;
    }
    emit(const AuthLoading());
    try {
      final res = await ApiClient.auth.login({
        'username': username,
        'password': password,
      });
      await ApiClient.saveToken(res.token);
      emit(AuthAuthenticated(token: res.token, user: res.user));
    } on Exception catch (e) {
      final isNetwork = e.toString().contains('SocketException') ||
          e.toString().contains('DioException');
      emit(AuthError(isNetwork ? 'network' : 'invalid'));
    }
  }

  Future<void> biometricLogin(String localizedReason) async {
    if (kIsWeb) {
      emit(const AuthError('biometric_unavailable'));
      return;
    }
    final localAuth = LocalAuthentication();
    final canCheck = await localAuth.canCheckBiometrics;
    final isSupported = await localAuth.isDeviceSupported();
    if (!canCheck && !isSupported) {
      emit(const AuthError('biometric_unavailable'));
      return;
    }
    final token = await ApiClient.getToken();
    if (token == null) {
      emit(const AuthError('no_stored_token'));
      return;
    }
    try {
      final ok = await localAuth.authenticate(
        localizedReason: localizedReason,
        options: const AuthenticationOptions(biometricOnly: false),
      );
      if (ok) {
        emit(AuthAuthenticated(token: token, user: const {}));
      }
    } on Exception {
      emit(const AuthError('biometric_failed'));
    }
  }

  Future<void> logout() async {
    await ApiClient.clearToken();
    emit(const AuthInitial());
  }
}
