import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/offline/offline_database.dart';
import 'package:frontend/core/offline/sync_manager.dart';

void main() {
  late OfflineDatabase db;
  late SyncManager syncManager;

  setUp(() {
    db = OfflineDatabase(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  group('OfflineDatabase & SyncManager Tests', () {
    test('Can write and read from database', () async {
      await db
          .into(db.formsCache)
          .insert(
            FormsCacheCompanion.insert(
              id: '1',
              orgId: 'org1',
              projectId: 'proj1',
              name: 'Test Form',
              description: 'Desc',
              schemaJson: '{}',
            ),
          );

      final forms = await db.select(db.formsCache).get();
      expect(forms.length, 1);
      expect(forms.first.name, 'Test Form');
    });

    test('SyncManager syncDelta applies updates and tombstones', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/sync')) {
          return http.Response(
            jsonEncode({
              'updated': [
                {
                  'id': 'f1',
                  'orgId': 'o1',
                  'projectId': 'p1',
                  'name': 'Synced Form',
                  'description': 'Updated description',
                  'schemaJson': '{"version": 1}',
                  'lastSyncedAt': '2026-06-07T12:00:00Z',
                },
              ],
              'tombstones': [
                {
                  'entity_type': 'forms',
                  'entity_id': 'f2',
                  'deleted_at': '2026-06-07T12:00:00Z',
                },
                {
                  'entity_type': 'responses',
                  'entity_id': 'r2',
                  'deleted_at': '2026-06-07T12:00:00Z',
                },
              ],
            }),
            200,
          );
        }
        return http.Response('Not found', 404);
      });

      syncManager = SyncManager(db: db, client: mockClient);

      // Pre-populate database with f2 (form) and r2 (response) to test tombstone deletion
      await db
          .into(db.formsCache)
          .insert(
            FormsCacheCompanion.insert(
              id: 'f2',
              orgId: 'o1',
              projectId: 'p1',
              name: 'Form to delete',
              description: 'Will be deleted',
              schemaJson: '{}',
            ),
          );
      await db
          .into(db.offlineResponses)
          .insert(
            OfflineResponsesCompanion.insert(
              id: 'r2',
              formId: 'f2',
              commitId: 'c1',
              answersJson: '{}',
              status: 'pending',
              createdAt: DateTime.now(),
            ),
          );

      // Verify they exist
      var forms = await db.select(db.formsCache).get();
      var responses = await db.select(db.offlineResponses).get();
      expect(forms.length, 1);
      expect(responses.length, 1);

      // Sync
      await syncManager.syncDelta('http://mock', 'token');

      // Verify f1 is added, f2 is deleted, and r2 is deleted
      forms = await db.select(db.formsCache).get();
      responses = await db.select(db.offlineResponses).get();

      expect(forms.length, 1);
      expect(forms.first.id, 'f1');
      expect(forms.first.name, 'Synced Form');
      expect(responses.length, 0);

      // Verify tombstones are logged locally
      final tombstones = await db.select(db.tombstones).get();
      expect(tombstones.length, 2);
    });

    test('SyncManager syncPendingResponses sends pending responses', () async {
      final List<Map<String, dynamic>> submissions = [];
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/responses')) {
          submissions.add(jsonDecode(request.body));
          return http.Response(jsonEncode({'status': 'success'}), 201);
        }
        return http.Response('Not found', 404);
      });

      syncManager = SyncManager(db: db, client: mockClient);

      await db
          .into(db.offlineResponses)
          .insert(
            OfflineResponsesCompanion.insert(
              id: 'r1',
              formId: 'f1',
              commitId: 'commit123',
              answersJson: '{"q1": "val1"}',
              status: 'pending',
              createdAt: DateTime.now(),
            ),
          );

      await syncManager.syncPendingResponses('http://mock', 'token');

      // Verify sent
      expect(submissions.length, 1);
      expect(submissions.first['commit_id'], 'commit123');

      // Verify status updated to synced
      final responses = await db.select(db.offlineResponses).get();
      expect(responses.length, 1);
      expect(responses.first.status, 'synced');
    });
  });
}
