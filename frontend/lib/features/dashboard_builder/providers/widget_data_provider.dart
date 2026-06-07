import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/widget_data_model.dart';
import 'canvas_state_provider.dart';
import 'dashboard_provider.dart';
import 'filter_state_provider.dart';

class WidgetDataState {
  final Map<String, WidgetDataResult> widgetResults;
  final bool isLoading;
  final String? error;

  const WidgetDataState({
    this.widgetResults = const {},
    this.isLoading = false,
    this.error,
  });

  WidgetDataState copyWith({
    Map<String, WidgetDataResult>? widgetResults,
    bool? isLoading,
    String? error,
  }) {
    return WidgetDataState(
      widgetResults: widgetResults ?? this.widgetResults,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class WidgetDataNotifier extends Notifier<WidgetDataState> {
  final String arg; // dashboardId or public token
  Timer? _refreshTimer;
  ProviderSubscription? _filterSubscription;

  WidgetDataNotifier(this.arg);

  @override
  WidgetDataState build() {
    _filterSubscription = ref.listen<Map<String, dynamic>>(
      filterStateProvider,
      (previous, next) {
        refreshData();
      },
    );

    ref.onDispose(() {
      _refreshTimer?.cancel();
      _filterSubscription?.close();
    });

    return const WidgetDataState();
  }

  Future<void> refreshData({bool isPublic = false}) async {
    state = state.copyWith(isLoading: true);
    final filterState = ref.read(filterStateProvider);
    final service = ref.read(dashboardServiceProvider);

    try {
      Map<String, WidgetDataResult> data;
      if (isPublic) {
        data = await service.getPublicDashboardData(
          publicToken: arg,
          filterState: filterState,
        );
      } else {
        final token = ref.read(authTokenProvider);
        data = await service.getCanvasData(
          dashboardId: arg,
          token: token,
          filterState: filterState,
        );
      }
      state = state.copyWith(widgetResults: data, isLoading: false, error: null);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  void setupAutoRefresh({required bool enabled, required int intervalSeconds, bool isPublic = false}) {
    _refreshTimer?.cancel();
    if (!enabled) return;

    final duration = Duration(seconds: intervalSeconds.clamp(10, 3600));
    _refreshTimer = Timer.periodic(duration, (_) {
      refreshData(isPublic: isPublic);
    });
  }
}

final widgetDataProvider = NotifierProvider.family<WidgetDataNotifier, WidgetDataState, String>((arg) {
  return WidgetDataNotifier(arg);
});

