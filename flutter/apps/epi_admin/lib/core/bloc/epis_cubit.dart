import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';

class EpisState extends Equatable {
  const EpisState({
    this.isLoading = false,
    this.error,
    this.epis = const [],
    this.query = '',
    this.filterCritical = false,
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;
  final String query;
  final bool filterCritical;

  List<Epi> get filtered {
    var result = epis;
    if (filterCritical) {
      result = result.where((e) => e.isCriticalStock).toList();
    }
    if (query.isNotEmpty) {
      final q = query.toLowerCase();
      result = result.where((e) {
        return e.name.toLowerCase().contains(q) ||
            (e.caNumber?.toLowerCase().contains(q) ?? false) ||
            (e.code?.toLowerCase().contains(q) ?? false);
      }).toList();
    }
    return result;
  }

  EpisState _copyWith({
    bool? isLoading,
    String? error,
    List<Epi>? epis,
    String? query,
    bool? filterCritical,
  }) =>
      EpisState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        epis: epis ?? this.epis,
        query: query ?? this.query,
        filterCritical: filterCritical ?? this.filterCritical,
      );

  @override
  List<Object?> get props => [isLoading, error, epis, query, filterCritical];
}

class EpisCubit extends Cubit<EpisState> {
  EpisCubit() : super(const EpisState());

  Future<void> load() async {
    emit(const EpisState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final epis = bootstrap.epis.map(Epi.fromJson).toList();
      emit(EpisState(epis: epis));
    } on Exception catch (e) {
      emit(EpisState(error: e.toString()));
    }
  }

  void search(String query) {
    emit(state._copyWith(query: query));
  }

  void toggleCriticalFilter() {
    emit(state._copyWith(filterCritical: !state.filterCritical));
  }

  Future<void> createEpi(Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.createEpi({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateEpi(int id, Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.updateEpi(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> deleteEpi(int id) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.deleteEpi(id, actorUserId: ApiClient.actorUserId);
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> _reloadEpis() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    final epis = bootstrap.epis.map(Epi.fromJson).toList();
    emit(EpisState(epis: epis));
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['error'] is Map && data['error']['message'] != null) {
        return data['error']['message'].toString();
      }
      if (data is Map && data['error'] != null) {
        return data['error'].toString();
      }
    }
    return e.toString();
  }
}
