import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:drift/drift.dart';
import 'offline_database.dart';

class SyncManager {
  final OfflineDatabase db;
  final http.Client client;

  SyncManager({required this.db, http.Client? client})
    : client = client ?? http.Client();

  /// Fetches delta changes from the server since the last sync timestamp
  /// and updates the local cache.
  Future<void> syncDelta(String baseUrl, String authToken) async {
    final query = db.select(db.formsCache)
      ..orderBy([
        (t) =>
            OrderingTerm(expression: t.lastSyncedAt, mode: OrderingMode.desc),
      ])
      ..limit(1);
    final latestForm = await query.getSingleOrNull();
    final lastSyncedAt = latestForm?.lastSyncedAt;

    String url = '$baseUrl/api/internal/v1/sync';
    if (lastSyncedAt != null) {
      url +=
          '?last_synced_at=${Uri.encodeComponent(lastSyncedAt.toUtc().toIso8601String())}';
    }

    final response = await client.get(
      Uri.parse(url),
      headers: {
        'Authorization': 'Bearer $authToken',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Failed to fetch sync delta: ${response.statusCode} ${response.body}',
      );
    }

    final data = jsonDecode(response.body);
    final updated = data['updated'] as List<dynamic>? ?? [];
    final tombstones = data['tombstones'] as List<dynamic>? ?? [];

    await db.transaction(() async {
      // Apply updates to FormsCache
      for (final form in updated) {
        final id = form['id'] as String;
        final orgId = form['orgId'] as String;
        final projectId = form['projectId'] as String;
        final name = form['name'] as String;
        final description = form['description'] as String? ?? '';
        final schemaJson = form['schemaJson'] is Map
            ? jsonEncode(form['schemaJson'])
            : (form['schemaJson'] as String? ?? '');
        final lastSyncedAtStr = form['lastSyncedAt'] as String?;
        final syncedTime = lastSyncedAtStr != null
            ? DateTime.parse(lastSyncedAtStr)
            : DateTime.now();

        await db
            .into(db.formsCache)
            .insertOnConflictUpdate(
              FormsCacheCompanion.insert(
                id: id,
                orgId: orgId,
                projectId: projectId,
                name: name,
                description: description,
                schemaJson: schemaJson,
                lastSyncedAt: Value(syncedTime),
              ),
            );
      }

      // Apply tombstones
      for (final tomb in tombstones) {
        final entityType = tomb['entity_type'] as String;
        final entityId = tomb['entity_id'] as String;
        final deletedAtStr = tomb['deleted_at'] as String?;
        final deletedAt = deletedAtStr != null
            ? DateTime.parse(deletedAtStr)
            : DateTime.now();

        // Write to tombstones table locally
        await db
            .into(db.tombstones)
            .insertOnConflictUpdate(
              TombstonesCompanion.insert(
                entityType: entityType,
                entityId: entityId,
                deletedAt: deletedAt,
              ),
            );

        // Purge records from local cache
        if (entityType == 'forms') {
          await (db.delete(
            db.formsCache,
          )..where((tbl) => tbl.id.equals(entityId))).go();
        } else if (entityType == 'responses') {
          await (db.delete(
            db.offlineResponses,
          )..where((tbl) => tbl.id.equals(entityId))).go();
        }
      }
    });
  }

  /// Uploads pending offline responses to the server.
  Future<void> syncPendingResponses(String baseUrl, String authToken) async {
    final pendingQuery = db.select(db.offlineResponses)
      ..where((tbl) => tbl.status.equals('pending'));
    final pending = await pendingQuery.get();

    for (final response in pending) {
      final url = '$baseUrl/api/v1/forms/${response.formId}/responses';
      try {
        final responseBody = {
          'commit_id': response.commitId,
          'answers': jsonDecode(response.answersJson),
        };

        final res = await client.post(
          Uri.parse(url),
          headers: {
            'Authorization': 'Bearer $authToken',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(responseBody),
        );

        if (res.statusCode == 200 || res.statusCode == 201) {
          await (db.update(db.offlineResponses)
                ..where((t) => t.id.equals(response.id)))
              .write(const OfflineResponsesCompanion(status: Value('synced')));
        } else if (res.statusCode == 409) {
          await (db.update(
            db.offlineResponses,
          )..where((t) => t.id.equals(response.id))).write(
            const OfflineResponsesCompanion(status: Value('conflict')),
          );
        } else {
          await (db.update(db.offlineResponses)
                ..where((t) => t.id.equals(response.id)))
              .write(const OfflineResponsesCompanion(status: Value('failed')));
        }
      } catch (e) {
        await (db.update(db.offlineResponses)
              ..where((t) => t.id.equals(response.id)))
            .write(const OfflineResponsesCompanion(status: Value('failed')));
      }
    }
  }
}
