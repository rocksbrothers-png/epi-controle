import 'package:equatable/equatable.dart';

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
  });
  final String token;
  final Map<String, dynamic> user;
  final List<String> permissions;
  @override
  List<Object?> get props => [token, permissions];
}

final class AuthError extends AuthState {
  const AuthError(this.code);
  // 'empty' | 'invalid' | 'network' | 'biometric_unavailable' | 'biometric_failed' | 'no_stored_token'
  final String code;
  @override
  List<Object?> get props => [code];
}
