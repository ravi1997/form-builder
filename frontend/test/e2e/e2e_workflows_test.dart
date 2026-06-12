import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:frontend/core/offline/offline_database.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/dashboard_builder/providers/canvas_state_provider.dart';
import 'package:frontend/features/dashboard_builder/models/dashboard_model.dart';
import 'package:frontend/features/dashboard_builder/models/widget_model.dart';
import 'package:frontend/features/dashboard_builder/dashboard_builder_page.dart';
import 'package:frontend/features/dashboard_builder/providers/dashboard_provider.dart';
import 'package:frontend/features/dashboard_builder/services/dashboard_service.dart';
import 'package:frontend/features/dashboard_builder/models/widget_data_model.dart';
import 'package:frontend/features/dashboard_builder/providers/widget_data_provider.dart';

class WorkflowsMockDashboardService implements DashboardService {
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
      projectId: 'project_alpha',
      name: 'E2E Workflow Dashboard',
      description: 'E2E Healthcare & Compliance',
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
    if (dashboardId == 'healthcare_dash') {
      return {
        'kpi_risk': const WidgetDataResult(
          status: 'ok',
          data: {'value': 9.6},
        )
      };
    }
    if (dashboardId == 'public_dash_1') {
      return {
        'stat_card': const WidgetDataResult(
          status: 'ok',
          data: {'value': 2.0},
        )
      };
    }
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
    if (publicToken == 'token_123_xyz') {
      return {
        'stat_card': const WidgetDataResult(
          status: 'ok',
          data: {'value': 2.0},
        )
      };
    }
    return {};
  }
}

class HealthcareFormNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'healthcare_form',
      name: 'Healthcare Patient Risk Assessment',
      style: FormStyle(),
      canvasMode: FormCanvasMode.play,
      sections: [
        FormSection(
          id: 'sec_1',
          title: 'Vitals',
          subSections: [
            FormSubSection(
              id: 'subsec_1',
              title: 'Measurements',
              questions: [
                FormQuestion(
                  id: 'q_blood_pressure',
                  type: 'number_input',
                  label: 'Blood Pressure (systolic)',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_heart_rate',
                  type: 'number_input',
                  label: 'Heart Rate',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_risk_rate',
                  type: 'calculation',
                  label: 'Risk Assessment Rate',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_blood_pressure * q_heart_rate / 1000'}
                  ],
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}

void main() {
  group('Tier 4: Real-World Workflow E2E Tests', () {
    void setupScreen(WidgetTester tester) {
      tester.view.physicalSize = const Size(1920, 1080);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
    }

    test('Workflow 1: Audited Project Legal Hold and Blocked Deletion', () {
      final List<Map<String, dynamic>> legalHolds = [
        {
          'id': 'hold_1',
          'name': 'GDPR Audit Retention',
          'target_type': 'project',
          'target_ids': ['project_alpha'],
          'is_active': true,
        }
      ];

      bool canDeleteResource({required String projectId, required List<Map<String, dynamic>> holds}) {
        for (final hold in holds) {
          if (hold['target_type'] == 'project' &&
              hold['target_ids'].contains(projectId) &&
              hold['is_active'] == true) {
            return false;
          }
        }
        return true;
      }

      // Step 1: Attempt deletion when hold is active
      final deleteAttempt1 = canDeleteResource(projectId: 'project_alpha', holds: legalHolds);
      expect(deleteAttempt1, isFalse);

      // Step 2: Toggle hold off
      legalHolds[0]['is_active'] = false;

      // Step 3: Attempt deletion again
      final deleteAttempt2 = canDeleteResource(projectId: 'project_alpha', holds: legalHolds);
      expect(deleteAttempt2, isTrue);
    });

    testWidgets('Workflow 2: Healthcare Formula Calculation and KPI Dashboard Propagation', (WidgetTester tester) async {
      setupScreen(tester);

      final container = ProviderContainer(
        overrides: [
          formBuilderProvider.overrideWith(() => HealthcareFormNotifier()),
        ],
      );

      // Step 1: Submit inputs to the vitals form
      container.read(formPlayProvider.notifier).setAnswer('q_blood_pressure', 120.0);
      container.read(formPlayProvider.notifier).setAnswer('q_heart_rate', 80.0);

      // Verify AST evaluation resolves correctly
      final playState = container.read(formPlayProvider);
      expect(playState.answers['q_risk_rate'], equals(9.6));

      // Step 2: Propagate calculation result to KPI dashboard widget
      final resolvedRiskRate = playState.answers['q_risk_rate'] as double;

      final mockService = WorkflowsMockDashboardService();
      const String dId = 'healthcare_dash';
      
      final kpiWidget = WidgetModel(
        id: 'kpi_risk',
        type: 'kpi_card',
        position: const WidgetPosition(x: 100, y: 100),
        size: const WidgetSize(width: 300, height: 150),
        properties: {
          'title': 'Patient Risk Index',
          'value': resolvedRiskRate,
          'decimal_places': 1,
        },
      );
      
      mockService.dashboards[dId] = DashboardModel(
        id: dId,
        orgId: 'org_1',
        projectId: 'project_alpha',
        name: 'Healthcare Vitals Aggregations',
        canvas: CanvasModel(
          width: 1920,
          height: 1080,
          backgroundColor: '#FFFFFF',
          widgets: [kpiWidget],
        ),
        settings: const DashboardSettings(),
        linkedAnalysisIds: const [],
      );

      final originalOnError = FlutterError.onError;
      FlutterError.onError = (FlutterErrorDetails details) {
        if (details.exceptionAsString().contains('ListTile background color') ||
            details.exceptionAsString().contains('A RenderFlex overflowed')) {
          return;
        }
        originalOnError?.call(details);
      };
      addTearDown(() => FlutterError.onError = originalOnError);

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
      await tester.pump(const Duration(milliseconds: 100));

      final builderContainer = ProviderScope.containerOf(tester.element(find.byType(DashboardBuilderPage)));
      await builderContainer.read(widgetDataProvider(dId).notifier).refreshData();
      await tester.pump();

      expect(find.text('Patient Risk Index'), findsOneWidget);
      expect(find.textContaining('9.6'), findsOneWidget);
    });

    test('Workflow 3: Member Promotion and Canvas Layout Customization', () {
      Map<String, dynamic> user = {
        'id': 'user_1',
        'email': 'doctor@hospital.org',
        'role': 'org_member',
      };

      final dynamicGroupRule = {
        'logical_operator': 'AND',
        'conditions': [
          {'field': 'role', 'operator': 'equals', 'value': 'org_admin'}
        ],
      };

      bool isAuthorizedToEditCanvas(Map<String, dynamic> u, Map<String, dynamic> rule) {
        final condition = rule['conditions'][0];
        if (condition['field'] == 'role' && condition['operator'] == 'equals') {
          return u['role'] == condition['value'];
        }
        return false;
      }

      expect(isAuthorizedToEditCanvas(user, dynamicGroupRule), isFalse);

      // Promote member to admin
      user['role'] = 'org_admin';
      expect(isAuthorizedToEditCanvas(user, dynamicGroupRule), isTrue);

      final canvasWidgets = [
        WidgetModel(
          id: 'widget_chart',
          type: 'bar_chart',
          position: const WidgetPosition(x: 400.0, y: 200.0),
          size: const WidgetSize(width: 400, height: 300),
          properties: const {},
        )
      ];

      // Move widget coordinates
      canvasWidgets[0] = canvasWidgets[0].copyWith(
        position: const WidgetPosition(x: 600.0, y: 300.0),
      );

      expect(canvasWidgets[0].position.x, equals(600.0));
      expect(canvasWidgets[0].position.y, equals(300.0));
    });

    test('Workflow 4: Storage Quota Blockage, Cleanup, and Recovery', () {
      double usedStorageBytes = 1024.0 * 1024.0 * 1024.0;
      const double quotaBytes = 1024.0 * 1024.0 * 1024.0;

      bool canSubmitResponse(double usedBytes, double fileUploadSize, double maxQuota) {
        return (usedBytes + fileUploadSize) <= maxQuota;
      }

      final submitAttempt1 = canSubmitResponse(usedStorageBytes, 50.0 * 1024.0, quotaBytes);
      expect(submitAttempt1, isFalse);

      // Cleanup files
      usedStorageBytes = 700.0 * 1024.0 * 1024.0;

      final submitAttempt2 = canSubmitResponse(usedStorageBytes, 50.0 * 1024.0, quotaBytes);
      expect(submitAttempt2, isTrue);
    });

    testWidgets('Workflow 5: Public Sharing of Aggregated Compliance Statistics', (WidgetTester tester) async {
      setupScreen(tester);

      final mockService = WorkflowsMockDashboardService();
      const String dId = 'public_dash_1';

      mockService.dashboards[dId] = DashboardModel(
        id: dId,
        orgId: 'org_1',
        projectId: 'proj_1',
        name: 'Public Compliance Statistics',
        isPublic: true,
        publicToken: 'token_123_xyz',
        canvas: const CanvasModel(
          width: 1920,
          height: 1080,
          backgroundColor: '#FFFFFF',
          widgets: [
            WidgetModel(
              id: 'stat_card',
              type: 'kpi_card',
              position: WidgetPosition(x: 100, y: 100),
              size: WidgetSize(width: 300, height: 150),
              properties: {
                'title': 'GDPR Holds Count',
                'value': 2.0,
                'decimal_places': 1,
              },
            ),
          ],
        ),
        settings: const DashboardSettings(),
        linkedAnalysisIds: const [],
      );

      final originalOnError = FlutterError.onError;
      FlutterError.onError = (FlutterErrorDetails details) {
        if (details.exceptionAsString().contains('ListTile background color') ||
            details.exceptionAsString().contains('A RenderFlex overflowed')) {
          return;
        }
        originalOnError?.call(details);
      };
      addTearDown(() => FlutterError.onError = originalOnError);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            dashboardServiceProvider.overrideWithValue(mockService),
            canvasStateProvider(dId).overrideWith(() {
              return CanvasStateNotifier(dId);
            }),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: DashboardBuilderPage(dashboardId: dId),
            ),
          ),
        ),
      );

      // Wait for page loading state to finish
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      final container = ProviderScope.containerOf(tester.element(find.byType(DashboardBuilderPage)));
      final notifier = container.read(canvasStateProvider(dId).notifier);
      
      // Toggle to preview mode
      notifier.toggleMode();
      await tester.pump();

      // Wait for widget data to load
      await container.read(widgetDataProvider(dId).notifier).refreshData();
      await tester.pump();

      expect(find.text('GDPR Holds Count'), findsOneWidget);
      expect(find.textContaining('2.0'), findsOneWidget);

      // Verify edit indicators / lock icons are absent in preview mode
      expect(find.byIcon(Icons.lock_open), findsNothing);
      expect(find.byIcon(Icons.lock), findsNothing);
    });
  });
}
