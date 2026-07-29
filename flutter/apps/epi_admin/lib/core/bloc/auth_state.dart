import 'package:equatable/equatable.dart';
import '../session/session_context.dart';

sealed class AuthState extends Equatable {
  const AuthState();
  @override
  List<Object?> get props => [];
}

final class AuthInitial extends AuthState {
  const AuthInitial();
}

final class AuthLoading extends AuthState {
  const AuthLoading();
}

final class AuthAuthenticated extends AuthState {
  const AuthAuthenticated({
    required this.token,
    required this.user,
    this.permissions = const [],
    this.sessionContext = SessionContext.empty,
  });
  final String token;
  final Map<String, dynamic> user;
  final List<String> permissions;
  final SessionContext sessionContext;

  /// Visibilidade estrutural por módulo (menu/rotas/deep links) — atalho
  /// para `sessionContext.moduleVisibility`, no mesmo padrão de
  /// [permissions] (que também espelha `sessionContext.permissions`).
  bool isModuleVisible(String module) => sessionContext.isModuleVisible(module);

  @override
  List<Object?> get props => [token, user, permissions, sessionContext];
}

final class AuthError extends AuthState {
  const AuthError(this.code);
  // 'empty' | 'invalid' | 'network' | 'biometric_unavailable' | 'biometric_failed' | 'no_stored_token'
  final String code;
  @override
  List<Object?> get props => [code];
}
