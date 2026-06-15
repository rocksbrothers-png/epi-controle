import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class UsersState extends Equatable {
  const UsersState({
    this.isLoading = false,
    this.error,
    this.users = const [],
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> users;
  final String query;

  List<Map<String, dynamic>> get filtered {
    if (query.isEmpty) return users;
    final q = query.toLowerCase();
    return users.where((u) {
      final username = (u['username'] as String? ?? '').toLowerCase();
      final fullName = (u['full_name'] as String? ?? '').toLowerCase();
      final role = (u['role'] as String? ?? '').toLowerCase();
      final companyName = (u['company_name'] as String? ?? '').toLowerCase();
      return username.contains(q) ||
          fullName.contains(q) ||
          role.contains(q) ||
          companyName.contains(q);
    }).toList();
  }

  UsersState _copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? users,
    String? query,
    bool clearError = false,
  }) =>
      UsersState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        users: users ?? this.users,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, users, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class UsersCubit extends Cubit<UsersState> {
  UsersCubit() : super(const UsersState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      emit(state._copyWith(isLoading: false, users: bootstrap.users));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void search(String query) => emit(state._copyWith(query: query));

  Future<void> createUser(Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.users.createUser({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadUsers();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateUser(int id, Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.users.updateUser(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadUsers();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> deleteUser(int id) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.users.deleteUser(id, actorUserId: ApiClient.actorUserId);
      await _reloadUsers();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> _reloadUsers() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    emit(state._copyWith(isLoading: false, users: bootstrap.users));
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
    }
    return e.toString();
  }
}
