import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:drift/drift.dart';
import '../../../core/offline/offline_database.dart';
import '../models/dashboard_model.dart';
import '../models/widget_data_model.dart';

class DashboardService {
  final http.Client client;
  final OfflineDatabase db;
  final String baseUrl;

  DashboardService({
    http.Client? client,
    required this.db,
    this.baseUrl = 'http://localhost:5000',
  }) : client = client ?? http.Client();

  Map<String, String> _headers(String token) => {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      };

  /// Lists all dashboards for a project. Loads from server first, falls back/caches to SQLite.
  Future<List<DashboardModel>> listDashboards({
    required String projectId,
    required String token,
    String? search,
    int page = 1,
    int perPage = 20,
  }) async {
    try {
      final searchParam = search != null ? '&search=${Uri.encodeComponent(search)}' : '';
      final url = '$baseUrl/api/internal/v1/dashboards?project_id=$projectId&page=$page&per_page=$perPage$searchParam';
      final response = await client.get(
        Uri.parse(url),
        headers: _headers(token),
      );

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        final List list = body['dashboards'] ?? [];
        final dashboards = list.map((item) => DashboardModel.fromJson(item)).toList();

        // Save metadata cache to SQLite
        for (final d in dashboards) {
          await _cacheDashboardLocally(d);
        }

        return dashboards;
      }
    } catch (_) {
      // Offline fallback: load from SQLite
    }

    // Load from local DB
    final query = db.select(db.dashboardsCache)..where((t) => t.projectId.equals(projectId));
    if (search != null && search.isNotEmpty) {
      query.where((t) => t.name.like('%$search%'));
    }
    final cachedRows = await query.get();
    return cachedRows.map((row) {
      return DashboardModel(
        id: row.id,
        orgId: row.orgId,
        projectId: row.projectId,
        name: row.name,
        description: row.description,
        isPublic: row.isPublic,
        publicToken: row.publicToken,
        canvas: CanvasModel.fromJson(jsonDecode(row.canvasJson)),
        settings: DashboardSettings.fromJson(jsonDecode(row.settingsJson)),
        linkedAnalysisIds: List<String>.from(jsonDecode(row.linkedAnalysisIdsJson)),
        updatedAt: row.lastSyncedAt,
      );
    }).toList();
  }

  /// Gets a dashboard by ID (loads full document including widgets).
  Future<DashboardModel> getDashboard(String dashboardId, String token) async {
    try {
      final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId';
      final response = await client.get(Uri.parse(url), headers: _headers(token));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        final dashboard = DashboardModel.fromJson(body['dashboard']);
        await _cacheDashboardLocally(dashboard);
        return dashboard;
      } else {
        throw Exception('Failed to load dashboard: ${response.statusCode}');
      }
    } catch (e) {
      // Offline fallback: load from local cache
      final row = await (db.select(db.dashboardsCache)..where((t) => t.id.equals(dashboardId))).getSingleOrNull();
      if (row != null) {
        return DashboardModel(
          id: row.id,
          orgId: row.orgId,
          projectId: row.projectId,
          name: row.name,
          description: row.description,
          isPublic: row.isPublic,
          publicToken: row.publicToken,
          canvas: CanvasModel.fromJson(jsonDecode(row.canvasJson)),
          settings: DashboardSettings.fromJson(jsonDecode(row.settingsJson)),
          linkedAnalysisIds: List<String>.from(jsonDecode(row.linkedAnalysisIdsJson)),
          updatedAt: row.lastSyncedAt,
        );
      }
      rethrow;
    }
  }

  /// Saves the complete canvas state to the backend.
  Future<DashboardModel> saveCanvas({
    required String dashboardId,
    required CanvasModel canvas,
    required String token,
  }) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId/canvas';
    final payload = {
      'canvas': canvas.toJson(),
    };
    final response = await client.put(
      Uri.parse(url),
      headers: _headers(token),
      body: jsonEncode(payload),
    );

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      final updated = DashboardModel.fromJson(body);
      await _cacheDashboardLocally(updated);
      return updated;
    } else {
      throw Exception('Failed to save canvas: ${response.body}');
    }
  }

  /// Creates a new dashboard.
  Future<DashboardModel> createDashboard({
    required String projectId,
    required String name,
    String? description,
    required String token,
  }) async {
    final url = '$baseUrl/api/internal/v1/dashboards';
    final payload = {
      'project_id': projectId,
      'name': name,
      'description': description,
    };
    final response = await client.post(
      Uri.parse(url),
      headers: _headers(token),
      body: jsonEncode(payload),
    );

    if (response.statusCode == 201) {
      final body = jsonDecode(response.body);
      final created = DashboardModel.fromJson(body['dashboard']);
      await _cacheDashboardLocally(created);
      return created;
    } else {
      throw Exception('Failed to create dashboard: ${response.body}');
    }
  }

  /// Updates dashboard metadata.
  Future<DashboardModel> updateDashboard({
    required String dashboardId,
    String? name,
    String? description,
    DashboardSettings? settings,
    required String token,
  }) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId';
    final Map<String, dynamic> payload = {};
    if (name != null) payload['name'] = name;
    if (description != null) payload['description'] = description;
    if (settings != null) payload['settings'] = settings.toJson();

    final response = await client.patch(
      Uri.parse(url),
      headers: _headers(token),
      body: jsonEncode(payload),
    );

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      final updated = DashboardModel.fromJson(body);
      await _cacheDashboardLocally(updated);
      return updated;
    } else {
      throw Exception('Failed to update dashboard metadata: ${response.body}');
    }
  }

  /// Deletes a dashboard.
  Future<void> deleteDashboard(String dashboardId, String token) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId';
    final response = await client.delete(Uri.parse(url), headers: _headers(token));

    if (response.statusCode == 200) {
      // Purge from local SQLite database cache
      await (db.delete(db.dashboardsCache)..where((t) => t.id.equals(dashboardId))).go();
    } else {
      throw Exception('Failed to delete dashboard: ${response.body}');
    }
  }

  /// Fetch dynamic data for all widgets in a dashboard.
  Future<Map<String, WidgetDataResult>> getCanvasData({
    required String dashboardId,
    required String token,
    Map<String, dynamic>? filterState,
  }) async {
    final filterStateStr = filterState != null ? '?filter_state=${Uri.encodeComponent(jsonEncode(filterState))}' : '';
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId/canvas/data$filterStateStr';
    final response = await client.get(Uri.parse(url), headers: _headers(token));

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      final Map<String, dynamic> widgetDataMap = body['widget_data'] ?? {};
      return widgetDataMap.map((key, val) => MapEntry(key, WidgetDataResult.fromJson(val)));
    } else {
      throw Exception('Failed to fetch canvas data: ${response.body}');
    }
  }

  /// Fetch dynamic data for an individual independent-refresh widget.
  Future<WidgetDataResult> getWidgetData({
    required String dashboardId,
    required String widgetId,
    required String token,
  }) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId/widgets/$widgetId/data';
    final response = await client.get(Uri.parse(url), headers: _headers(token));

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      return WidgetDataResult.fromJson(body);
    } else {
      throw Exception('Failed to fetch widget data: ${response.body}');
    }
  }

  /// Enable public sharing of a dashboard.
  Future<Map<String, dynamic>> enablePublicSharing(String dashboardId, String token) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId/public-token';
    final response = await client.post(Uri.parse(url), headers: _headers(token));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to enable public sharing: ${response.body}');
    }
  }

  /// Disable public sharing of a dashboard.
  Future<void> disablePublicSharing(String dashboardId, String token) async {
    final url = '$baseUrl/api/internal/v1/dashboards/$dashboardId/public-token';
    final response = await client.delete(Uri.parse(url), headers: _headers(token));

    if (response.statusCode != 200) {
      throw Exception('Failed to disable public sharing: ${response.body}');
    }
  }

  /// Unauthenticated access to public dashboard structure and data.
  Future<Map<String, dynamic>> getPublicDashboard({
    required String publicToken,
    Map<String, dynamic>? filterState,
  }) async {
    final filterStateStr = filterState != null ? '?filter_state=${Uri.encodeComponent(jsonEncode(filterState))}' : '';
    final url = '$baseUrl/api/v1/public/dashboards/$publicToken$filterStateStr';
    final response = await client.get(Uri.parse(url));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load public dashboard: ${response.statusCode}');
    }
  }

  /// Unauthenticated polling of public widget data.
  Future<Map<String, WidgetDataResult>> getPublicDashboardData({
    required String publicToken,
    Map<String, dynamic>? filterState,
  }) async {
    final filterStateStr = filterState != null ? '?filter_state=${Uri.encodeComponent(jsonEncode(filterState))}' : '';
    final url = '$baseUrl/api/v1/public/dashboards/$publicToken/data$filterStateStr';
    final response = await client.get(Uri.parse(url));

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body);
      final Map<String, dynamic> widgetDataMap = body['widget_data'] ?? {};
      return widgetDataMap.map((key, val) => MapEntry(key, WidgetDataResult.fromJson(val)));
    } else {
      throw Exception('Failed to load public dashboard data: ${response.statusCode}');
    }
  }

  /// Helper to cache a dashboard document in Drift table.
  Future<void> _cacheDashboardLocally(DashboardModel dashboard) async {
    await db.into(db.dashboardsCache).insertOnConflictUpdate(
          DashboardsCacheCompanion.insert(
            id: dashboard.id,
            orgId: dashboard.orgId,
            projectId: dashboard.projectId,
            name: dashboard.name,
            description: Value(dashboard.description),
            canvasJson: jsonEncode(dashboard.canvas.toJson()),
            settingsJson: jsonEncode(dashboard.settings.toJson()),
            linkedAnalysisIdsJson: jsonEncode(dashboard.linkedAnalysisIds),
            isPublic: Value(dashboard.isPublic),
            publicToken: Value(dashboard.publicToken),
            lastSyncedAt: Value(DateTime.now()),
          ),
        );
  }
}
