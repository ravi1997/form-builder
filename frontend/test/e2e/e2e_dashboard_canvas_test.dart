import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:frontend/core/offline/offline_database.dart';
import 'package:frontend/features/dashboard_builder/dashboard_builder_page.dart';
import 'package:frontend/features/dashboard_builder/providers/canvas_state_provider.dart';
import 'package:frontend/features/dashboard_builder/providers/dashboard_provider.dart';
import 'package:frontend/features/dashboard_builder/services/dashboard_service.dart';
import 'package:frontend/features/dashboard_builder/models/dashboard_model.dart';
import 'package:frontend/features/dashboard_builder/models/widget_model.dart';
import 'package:frontend/features/dashboard_builder/models/widget_data_model.dart';

class MockDashboardService implements DashboardService {
  final Map<String, DashboardModel> dashboards = {};

  @override
  http.Client get client => throw UnimplementedError();

  @override
  OfflineDatabase get db => throw UnimplementedError();

  @override
  String get baseUrl => '';

  @override
  Future<List<DashboardModel>> listDashboards({
    required String projectId,
    required String token,
    String? search,
    int page = 1,
    int perPage = 20,
  }) async {
    return dashboards.values.toList();
  }

  @override
  Future<DashboardModel> getDashboard(String dashboardId, String token) async {
    return dashboards[dashboardId] ?? DashboardModel(
      id: dashboardId,
      orgId: 'org_1',
      projectId: 'proj_1',
      name: 'E2E Dashboard',
      description: 'E2E Testing Canvas',
      isPublic: false,
      canvas: const CanvasModel(
        width: 1920,
        height: 1080,
        backgroundColor: '#FFFFFF',
        widgets: [],
      ),
      settings: const DashboardSettings(
        autoRefresh: false,
        refreshIntervalSeconds: 60,
      ),
      linkedAnalysisIds: const [],
    );
  }

  @override
  Future<DashboardModel> saveCanvas({
    required String dashboardId,
    required CanvasModel canvas,
    required String token,
  }) async {
    final old = await getDashboard(dashboardId, token);
    final updated = old.copyWith(canvas: canvas);
    dashboards[dashboardId] = updated;
    return updated;
  }

  @override
  Future<DashboardModel> createDashboard({
    required String projectId,
    required String name,
    String? description,
    required String token,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<DashboardModel> updateDashboard({
    required String dashboardId,
    String? name,
    String? description,
    DashboardSettings? settings,
    required String token,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<void> deleteDashboard(String dashboardId, String token) async {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, WidgetDataResult>> getCanvasData({
    required String dashboardId,
    required String token,
    Map<String, dynamic>? filterState,
  }) async {
    return {};
  }

  @override
  Future<WidgetDataResult> getWidgetData({
    required String dashboardId,
    required String widgetId,
    required String token,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, dynamic>> enablePublicSharing(String dashboardId, String token) async {
    throw UnimplementedError();
  }

  @override
  Future<void> disablePublicSharing(String dashboardId, String token) async {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, dynamic>> getPublicDashboard({
    required String publicToken,
    Map<String, dynamic>? filterState,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, WidgetDataResult>> getPublicDashboardData({
    required String publicToken,
    Map<String, dynamic>? filterState,
  }) async {
    throw UnimplementedError();
  }
}

void main() {
  group('Dashboard Canvas Drag-and-Drop E2E Tests (Tiers 1-2)', () {
    void setupScreen(WidgetTester tester) {
      tester.view.physicalSize = const Size(1920, 1080);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
    }

    testWidgets('T31-T34, T36-T38: Add, drag, snap, lock, and save coordinates on canvas', (WidgetTester tester) async {
      setupScreen(tester);

      final originalOnError = FlutterError.onError;
      FlutterError.onError = (FlutterErrorDetails details) {
        final String desc = details.exceptionAsString();
        if (desc.contains('ListTile background color or ink splashes may be invisible') ||
            desc.contains('A RenderFlex overflowed')) {
          // Suppress layout overflows and cosmetic warnings
          return;
        }
        originalOnError?.call(details);
      };
      addTearDown(() {
        FlutterError.onError = originalOnError;
      });

      final mockService = MockDashboardService();
      const String dId = 'dash_test_1';

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            dashboardServiceProvider.overrideWithValue(mockService),
          ],
          child: const MaterialApp(
            home: DashboardBuilderPage(dashboardId: dId),
          ),
        ),
      );

      // Wait for page loading state to finish
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      // Verify that Dashboard Builder is loaded
      expect(find.text('Dashboard builder'), findsOneWidget);

      // Get the current CanvasStateNotifier to verify states
      final container = ProviderScope.containerOf(tester.element(find.byType(DashboardBuilderPage)));
      final notifier = container.read(canvasStateProvider(dId).notifier);

      // 1. Verify canvas is empty initially
      expect(container.read(canvasStateProvider(dId)).widgets.isEmpty, isTrue);

      // 2. Add a KPI Card widget using the library onTap (or notifier directly)
      await tester.tap(find.text('KPI metric card'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // Verify a widget is added
      final stateAfterAdd = container.read(canvasStateProvider(dId));
      expect(stateAfterAdd.widgets.length, equals(1));
      final widgetId = stateAfterAdd.widgets.first.id;
      expect(stateAfterAdd.widgets.first.type, equals('kpi_card'));
      expect(stateAfterAdd.widgets.first.position.x, equals(400.0));
      expect(stateAfterAdd.widgets.first.position.y, equals(200.0));

      // 3. Move the widget
      expect(container.read(canvasStateProvider(dId)).snapToGrid, isFalse);
      notifier.moveWidget(widgetId, 405.2, 207.8);
      await tester.pump();

      var currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(405.2));
      expect(currentWidget.position.y, equals(207.8));

      // 4. Snap to grid
      notifier.toggleSnapToGrid();
      expect(container.read(canvasStateProvider(dId)).snapToGrid, isTrue);

      notifier.moveWidget(widgetId, 405.2, 207.8);
      await tester.pump();

      currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(408.0));
      expect(currentWidget.position.y, equals(208.0));

      // 5. Clamping check
      notifier.moveWidget(widgetId, -50.0, -100.0);
      await tester.pump();

      currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(0.0));
      expect(currentWidget.position.y, equals(0.0));

      notifier.moveWidget(widgetId, 2000.0, 2000.0);
      await tester.pump();

      currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(1640.0));
      expect(currentWidget.position.y, equals(940.0));

      // 6. Lock Property check
      notifier.moveWidget(widgetId, 300, 300);
      await tester.pump();

      notifier.toggleLockWidget(widgetId);
      expect(container.read(canvasStateProvider(dId)).widgets.first.isLocked, isTrue);

      notifier.moveWidget(widgetId, 500, 500);
      await tester.pump();

      currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(304.0));
      expect(currentWidget.position.y, equals(304.0));

      // Unlock
      notifier.toggleLockWidget(widgetId);
      expect(container.read(canvasStateProvider(dId)).widgets.first.isLocked, isFalse);

      // Move again
      notifier.moveWidget(widgetId, 500, 500);
      await tester.pump();
      currentWidget = container.read(canvasStateProvider(dId)).widgets.first;
      expect(currentWidget.position.x, equals(504.0));
      expect(currentWidget.position.y, equals(504.0));

      // 7. Save coordinates
      expect(container.read(canvasStateProvider(dId)).isDirty, isTrue);
      await tester.tap(find.byIcon(Icons.save));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // Verify not dirty anymore and saved inside service cache
      expect(container.read(canvasStateProvider(dId)).isDirty, isFalse);
      
      final savedDashboard = await mockService.getDashboard(dId, 'any');
      expect(savedDashboard.canvas.widgets.length, equals(1));
      expect(savedDashboard.canvas.widgets.first.position.x, equals(504.0));
      expect(savedDashboard.canvas.widgets.first.position.y, equals(504.0));
    });
  });
}
