import 'package:flutter_riverpod/flutter_riverpod.dart';

class FilterStateNotifier extends Notifier<Map<String, dynamic>> {
  @override
  Map<String, dynamic> build() {
    return {};
  }

  void updateFilter(String widgetId, dynamic value) {
    if (value == null) {
      final updated = Map<String, dynamic>.from(state)..remove(widgetId);
      state = updated;
    } else {
      state = {...state, widgetId: value};
    }
  }

  void clearAllFilters() {
    state = {};
  }
}

final filterStateProvider = NotifierProvider<FilterStateNotifier, Map<String, dynamic>>(() {
  return FilterStateNotifier();
});
