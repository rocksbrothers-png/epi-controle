import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:local_auth/local_auth.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';
import 'auth_state.dart';

class AuthCubit extends Cubit<AuthState> {
  AuthCubit() : super(const AuthInitial());

  Future<void> tryAutoLogin() async {
    final token = await ApiClient.getToken();
    if (token == null) return;

    // Otimista: restaura a sessão guardada de imediato (UX e offline-friendly).
    final stored = await ApiClient.getPermissions();
    emit(AuthAuthenticated(token: token, user: const {}, permissions: stored));

    // Reidrata identidade/permissões no backend. Se o access token estiver
    // expirado, o interceptor faz o refresh transparentemente; só caímos no
    // login se o refresh também falhar (interceptor limpa a sessão).
    try {
      final identity = AuthIdentity.fromMeJson(await ApiClient.fetchMe());
      await ApiClient.savePermissions(identity.permissions);
      final freshToken = await ApiClient.getToken() ?? token;
      emit(AuthAuthenticated(
        token: freshToken,
        user: identity.user,
        permissions: identity.permissions,
      ));
    } on Exception {
      // Se o interceptor derrubou a sessão (refresh falhou), volta ao login.
      if (await ApiClient.getToken() == null) {
        await ApiClient.clearSession();
        emit(const AuthInitial());
      }
      // Caso contrário (ex.: rede offline), mantém a sessão otimista.
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
      // Permissões e refresh token vêm no **topo** da resposta (não em `user`).
      final permissions = res.permissions;
      await ApiClient.saveToken(res.token);
      if (res.refreshToken != null && res.refreshToken!.isNotEmpty) {
        await ApiClient.saveRefreshToken(res.refreshToken!);
      }
      await ApiClient.savePermissions(permissions);
      emit(AuthAuthenticated(token: res.token, user: res.user, permissions: permissions));
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
    final permissions = await ApiClient.getPermissions();
    try {
      final ok = await localAuth.authenticate(
        localizedReason: localizedReason,
        options: const AuthenticationOptions(biometricOnly: false),
      );
      if (ok) {
        emit(AuthAuthenticated(token: token, user: const {}, permissions: permissions));
      }
    } on Exception {
      emit(const AuthError('biometric_failed'));
    }
  }

  Future<void> logout() async {
    await ApiClient.clearSession();
    emit(const AuthInitial());
  }
}
