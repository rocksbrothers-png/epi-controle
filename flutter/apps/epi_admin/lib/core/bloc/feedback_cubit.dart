import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';

class FeedbackState extends Equatable {
  const FeedbackState({
    this.isLoading = false,
    this.error,
    this.items = const [],
    this.statusFilter,
  });

  final bool isLoading;
  final String? error;
  final List<FeedbackItem> items;
  final String? statusFilter;

  FeedbackState _copyWith({
    bool? isLoading,
    String? error,
    List<FeedbackItem>? items,
    String? statusFilter,
    bool clearError = false,
    bool clearFilter = false,
  }) =>
      FeedbackState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        items: items ?? this.items,
        statusFilter:
            clearFilter ? null : (statusFilter ?? this.statusFilter),
      );

  @override
  List<Object?> get props => [isLoading, error, items, statusFilter];
}

class FeedbackCubit extends Cubit<FeedbackState> {
  FeedbackCubit() : super(const FeedbackState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final items = await ApiClient.feedback
          .getFeedbacks(status: state.statusFilter);
      emit(state._copyWith(isLoading: false, items: items));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<void> setFilter(String? status) async {
    emit(FeedbackState(statusFilter: status));
    await load();
  }

  Future<void> validate(int id) async {
    try {
      await ApiClient.feedback.managerValidate(feedbackId: id);
      await load();
    } on Exception catch (e) {
      emit(state._copyWith(error: e.toString()));
    }
  }

  Future<void> close(int id) async {
    try {
      await ApiClient.feedback.close(feedbackId: id);
      await load();
    } on Exception catch (e) {
      emit(state._copyWith(error: e.toString()));
    }
  }
}
