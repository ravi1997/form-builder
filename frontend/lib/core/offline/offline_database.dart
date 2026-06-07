import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

part 'offline_database.g.dart';

class FormsCache extends Table {
  TextColumn get id => text()();
  TextColumn get orgId => text()();
  TextColumn get projectId => text()();
  TextColumn get name => text()();
  TextColumn get description => text()();
  TextColumn get schemaJson => text()();
  DateTimeColumn get lastSyncedAt => dateTime().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

class OfflineResponses extends Table {
  TextColumn get id => text()();
  TextColumn get formId => text()();
  TextColumn get commitId => text()();
  TextColumn get answersJson => text()();
  TextColumn get status => text()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Tombstones extends Table {
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  DateTimeColumn get deletedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {entityType, entityId};
}

class DashboardsCache extends Table {
  TextColumn get id => text()();
  TextColumn get orgId => text()();
  TextColumn get projectId => text()();
  TextColumn get name => text()();
  TextColumn get description => text().nullable()();
  TextColumn get canvasJson => text()();
  TextColumn get settingsJson => text()();
  TextColumn get linkedAnalysisIdsJson => text()();
  BoolColumn get isPublic => boolean().withDefault(const Constant(false))();
  TextColumn get publicToken => text().nullable()();
  DateTimeColumn get lastSyncedAt => dateTime().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [FormsCache, OfflineResponses, Tombstones, DashboardsCache])
class OfflineDatabase extends _$OfflineDatabase {
  OfflineDatabase([QueryExecutor? e]) : super(e ?? _openConnection());

  @override
  int get schemaVersion => 1;
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'db.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
