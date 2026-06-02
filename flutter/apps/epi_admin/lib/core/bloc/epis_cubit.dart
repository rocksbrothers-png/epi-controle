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
}
