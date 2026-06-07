import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/offline/offline_database.dart';
import '../services/dashboard_service.dart';

final offlineDatabaseProvider = Provider<OfflineDatabase>((ref) {
  final db = OfflineDatabase();
  ref.onDispose(() => db.close());
  return db;
});

final dashboardServiceProvider = Provider<DashboardService>((ref) {
  final db = ref.watch(offlineDatabaseProvider);
  return DashboardService(db: db);
});

// A simple provider for user token (e.g. populated on login)
final authTokenProvider = Provider<String>((ref) => 'mock-token');

// A provider for currently selected project
final currentProjectIdProvider = Provider<String>((ref) => 'default-project');
