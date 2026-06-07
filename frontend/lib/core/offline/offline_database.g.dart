// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'offline_database.dart';

// ignore_for_file: type=lint
class $FormsCacheTable extends FormsCache
    with TableInfo<$FormsCacheTable, FormsCacheData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $FormsCacheTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _projectIdMeta = const VerificationMeta(
    'projectId',
  );
  @override
  late final GeneratedColumn<String> projectId = GeneratedColumn<String>(
    'project_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _descriptionMeta = const VerificationMeta(
    'description',
  );
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
    'description',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _schemaJsonMeta = const VerificationMeta(
    'schemaJson',
  );
  @override
  late final GeneratedColumn<String> schemaJson = GeneratedColumn<String>(
    'schema_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lastSyncedAtMeta = const VerificationMeta(
    'lastSyncedAt',
  );
  @override
  late final GeneratedColumn<DateTime> lastSyncedAt = GeneratedColumn<DateTime>(
    'last_synced_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    orgId,
    projectId,
    name,
    description,
    schemaJson,
    lastSyncedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'forms_cache';
  @override
  VerificationContext validateIntegrity(
    Insertable<FormsCacheData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('org_id')) {
      context.handle(
        _orgIdMeta,
        orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta),
      );
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('project_id')) {
      context.handle(
        _projectIdMeta,
        projectId.isAcceptableOrUnknown(data['project_id']!, _projectIdMeta),
      );
    } else if (isInserting) {
      context.missing(_projectIdMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
        _descriptionMeta,
        description.isAcceptableOrUnknown(
          data['description']!,
          _descriptionMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_descriptionMeta);
    }
    if (data.containsKey('schema_json')) {
      context.handle(
        _schemaJsonMeta,
        schemaJson.isAcceptableOrUnknown(data['schema_json']!, _schemaJsonMeta),
      );
    } else if (isInserting) {
      context.missing(_schemaJsonMeta);
    }
    if (data.containsKey('last_synced_at')) {
      context.handle(
        _lastSyncedAtMeta,
        lastSyncedAt.isAcceptableOrUnknown(
          data['last_synced_at']!,
          _lastSyncedAtMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  FormsCacheData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return FormsCacheData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      orgId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}org_id'],
      )!,
      projectId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}project_id'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      description: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}description'],
      )!,
      schemaJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}schema_json'],
      )!,
      lastSyncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_synced_at'],
      ),
    );
  }

  @override
  $FormsCacheTable createAlias(String alias) {
    return $FormsCacheTable(attachedDatabase, alias);
  }
}

class FormsCacheData extends DataClass implements Insertable<FormsCacheData> {
  final String id;
  final String orgId;
  final String projectId;
  final String name;
  final String description;
  final String schemaJson;
  final DateTime? lastSyncedAt;
  const FormsCacheData({
    required this.id,
    required this.orgId,
    required this.projectId,
    required this.name,
    required this.description,
    required this.schemaJson,
    this.lastSyncedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['org_id'] = Variable<String>(orgId);
    map['project_id'] = Variable<String>(projectId);
    map['name'] = Variable<String>(name);
    map['description'] = Variable<String>(description);
    map['schema_json'] = Variable<String>(schemaJson);
    if (!nullToAbsent || lastSyncedAt != null) {
      map['last_synced_at'] = Variable<DateTime>(lastSyncedAt);
    }
    return map;
  }

  FormsCacheCompanion toCompanion(bool nullToAbsent) {
    return FormsCacheCompanion(
      id: Value(id),
      orgId: Value(orgId),
      projectId: Value(projectId),
      name: Value(name),
      description: Value(description),
      schemaJson: Value(schemaJson),
      lastSyncedAt: lastSyncedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(lastSyncedAt),
    );
  }

  factory FormsCacheData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return FormsCacheData(
      id: serializer.fromJson<String>(json['id']),
      orgId: serializer.fromJson<String>(json['orgId']),
      projectId: serializer.fromJson<String>(json['projectId']),
      name: serializer.fromJson<String>(json['name']),
      description: serializer.fromJson<String>(json['description']),
      schemaJson: serializer.fromJson<String>(json['schemaJson']),
      lastSyncedAt: serializer.fromJson<DateTime?>(json['lastSyncedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'orgId': serializer.toJson<String>(orgId),
      'projectId': serializer.toJson<String>(projectId),
      'name': serializer.toJson<String>(name),
      'description': serializer.toJson<String>(description),
      'schemaJson': serializer.toJson<String>(schemaJson),
      'lastSyncedAt': serializer.toJson<DateTime?>(lastSyncedAt),
    };
  }

  FormsCacheData copyWith({
    String? id,
    String? orgId,
    String? projectId,
    String? name,
    String? description,
    String? schemaJson,
    Value<DateTime?> lastSyncedAt = const Value.absent(),
  }) => FormsCacheData(
    id: id ?? this.id,
    orgId: orgId ?? this.orgId,
    projectId: projectId ?? this.projectId,
    name: name ?? this.name,
    description: description ?? this.description,
    schemaJson: schemaJson ?? this.schemaJson,
    lastSyncedAt: lastSyncedAt.present ? lastSyncedAt.value : this.lastSyncedAt,
  );
  FormsCacheData copyWithCompanion(FormsCacheCompanion data) {
    return FormsCacheData(
      id: data.id.present ? data.id.value : this.id,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      projectId: data.projectId.present ? data.projectId.value : this.projectId,
      name: data.name.present ? data.name.value : this.name,
      description: data.description.present
          ? data.description.value
          : this.description,
      schemaJson: data.schemaJson.present
          ? data.schemaJson.value
          : this.schemaJson,
      lastSyncedAt: data.lastSyncedAt.present
          ? data.lastSyncedAt.value
          : this.lastSyncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('FormsCacheData(')
          ..write('id: $id, ')
          ..write('orgId: $orgId, ')
          ..write('projectId: $projectId, ')
          ..write('name: $name, ')
          ..write('description: $description, ')
          ..write('schemaJson: $schemaJson, ')
          ..write('lastSyncedAt: $lastSyncedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    orgId,
    projectId,
    name,
    description,
    schemaJson,
    lastSyncedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is FormsCacheData &&
          other.id == this.id &&
          other.orgId == this.orgId &&
          other.projectId == this.projectId &&
          other.name == this.name &&
          other.description == this.description &&
          other.schemaJson == this.schemaJson &&
          other.lastSyncedAt == this.lastSyncedAt);
}

class FormsCacheCompanion extends UpdateCompanion<FormsCacheData> {
  final Value<String> id;
  final Value<String> orgId;
  final Value<String> projectId;
  final Value<String> name;
  final Value<String> description;
  final Value<String> schemaJson;
  final Value<DateTime?> lastSyncedAt;
  final Value<int> rowid;
  const FormsCacheCompanion({
    this.id = const Value.absent(),
    this.orgId = const Value.absent(),
    this.projectId = const Value.absent(),
    this.name = const Value.absent(),
    this.description = const Value.absent(),
    this.schemaJson = const Value.absent(),
    this.lastSyncedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  FormsCacheCompanion.insert({
    required String id,
    required String orgId,
    required String projectId,
    required String name,
    required String description,
    required String schemaJson,
    this.lastSyncedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       orgId = Value(orgId),
       projectId = Value(projectId),
       name = Value(name),
       description = Value(description),
       schemaJson = Value(schemaJson);
  static Insertable<FormsCacheData> custom({
    Expression<String>? id,
    Expression<String>? orgId,
    Expression<String>? projectId,
    Expression<String>? name,
    Expression<String>? description,
    Expression<String>? schemaJson,
    Expression<DateTime>? lastSyncedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (orgId != null) 'org_id': orgId,
      if (projectId != null) 'project_id': projectId,
      if (name != null) 'name': name,
      if (description != null) 'description': description,
      if (schemaJson != null) 'schema_json': schemaJson,
      if (lastSyncedAt != null) 'last_synced_at': lastSyncedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  FormsCacheCompanion copyWith({
    Value<String>? id,
    Value<String>? orgId,
    Value<String>? projectId,
    Value<String>? name,
    Value<String>? description,
    Value<String>? schemaJson,
    Value<DateTime?>? lastSyncedAt,
    Value<int>? rowid,
  }) {
    return FormsCacheCompanion(
      id: id ?? this.id,
      orgId: orgId ?? this.orgId,
      projectId: projectId ?? this.projectId,
      name: name ?? this.name,
      description: description ?? this.description,
      schemaJson: schemaJson ?? this.schemaJson,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (projectId.present) {
      map['project_id'] = Variable<String>(projectId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (schemaJson.present) {
      map['schema_json'] = Variable<String>(schemaJson.value);
    }
    if (lastSyncedAt.present) {
      map['last_synced_at'] = Variable<DateTime>(lastSyncedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('FormsCacheCompanion(')
          ..write('id: $id, ')
          ..write('orgId: $orgId, ')
          ..write('projectId: $projectId, ')
          ..write('name: $name, ')
          ..write('description: $description, ')
          ..write('schemaJson: $schemaJson, ')
          ..write('lastSyncedAt: $lastSyncedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $OfflineResponsesTable extends OfflineResponses
    with TableInfo<$OfflineResponsesTable, OfflineResponse> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OfflineResponsesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formIdMeta = const VerificationMeta('formId');
  @override
  late final GeneratedColumn<String> formId = GeneratedColumn<String>(
    'form_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _commitIdMeta = const VerificationMeta(
    'commitId',
  );
  @override
  late final GeneratedColumn<String> commitId = GeneratedColumn<String>(
    'commit_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _answersJsonMeta = const VerificationMeta(
    'answersJson',
  );
  @override
  late final GeneratedColumn<String> answersJson = GeneratedColumn<String>(
    'answers_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    formId,
    commitId,
    answersJson,
    status,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'offline_responses';
  @override
  VerificationContext validateIntegrity(
    Insertable<OfflineResponse> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('form_id')) {
      context.handle(
        _formIdMeta,
        formId.isAcceptableOrUnknown(data['form_id']!, _formIdMeta),
      );
    } else if (isInserting) {
      context.missing(_formIdMeta);
    }
    if (data.containsKey('commit_id')) {
      context.handle(
        _commitIdMeta,
        commitId.isAcceptableOrUnknown(data['commit_id']!, _commitIdMeta),
      );
    } else if (isInserting) {
      context.missing(_commitIdMeta);
    }
    if (data.containsKey('answers_json')) {
      context.handle(
        _answersJsonMeta,
        answersJson.isAcceptableOrUnknown(
          data['answers_json']!,
          _answersJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_answersJsonMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  OfflineResponse map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OfflineResponse(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      formId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}form_id'],
      )!,
      commitId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}commit_id'],
      )!,
      answersJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}answers_json'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $OfflineResponsesTable createAlias(String alias) {
    return $OfflineResponsesTable(attachedDatabase, alias);
  }
}

class OfflineResponse extends DataClass implements Insertable<OfflineResponse> {
  final String id;
  final String formId;
  final String commitId;
  final String answersJson;
  final String status;
  final DateTime createdAt;
  const OfflineResponse({
    required this.id,
    required this.formId,
    required this.commitId,
    required this.answersJson,
    required this.status,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['form_id'] = Variable<String>(formId);
    map['commit_id'] = Variable<String>(commitId);
    map['answers_json'] = Variable<String>(answersJson);
    map['status'] = Variable<String>(status);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  OfflineResponsesCompanion toCompanion(bool nullToAbsent) {
    return OfflineResponsesCompanion(
      id: Value(id),
      formId: Value(formId),
      commitId: Value(commitId),
      answersJson: Value(answersJson),
      status: Value(status),
      createdAt: Value(createdAt),
    );
  }

  factory OfflineResponse.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OfflineResponse(
      id: serializer.fromJson<String>(json['id']),
      formId: serializer.fromJson<String>(json['formId']),
      commitId: serializer.fromJson<String>(json['commitId']),
      answersJson: serializer.fromJson<String>(json['answersJson']),
      status: serializer.fromJson<String>(json['status']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'formId': serializer.toJson<String>(formId),
      'commitId': serializer.toJson<String>(commitId),
      'answersJson': serializer.toJson<String>(answersJson),
      'status': serializer.toJson<String>(status),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  OfflineResponse copyWith({
    String? id,
    String? formId,
    String? commitId,
    String? answersJson,
    String? status,
    DateTime? createdAt,
  }) => OfflineResponse(
    id: id ?? this.id,
    formId: formId ?? this.formId,
    commitId: commitId ?? this.commitId,
    answersJson: answersJson ?? this.answersJson,
    status: status ?? this.status,
    createdAt: createdAt ?? this.createdAt,
  );
  OfflineResponse copyWithCompanion(OfflineResponsesCompanion data) {
    return OfflineResponse(
      id: data.id.present ? data.id.value : this.id,
      formId: data.formId.present ? data.formId.value : this.formId,
      commitId: data.commitId.present ? data.commitId.value : this.commitId,
      answersJson: data.answersJson.present
          ? data.answersJson.value
          : this.answersJson,
      status: data.status.present ? data.status.value : this.status,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OfflineResponse(')
          ..write('id: $id, ')
          ..write('formId: $formId, ')
          ..write('commitId: $commitId, ')
          ..write('answersJson: $answersJson, ')
          ..write('status: $status, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, formId, commitId, answersJson, status, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OfflineResponse &&
          other.id == this.id &&
          other.formId == this.formId &&
          other.commitId == this.commitId &&
          other.answersJson == this.answersJson &&
          other.status == this.status &&
          other.createdAt == this.createdAt);
}

class OfflineResponsesCompanion extends UpdateCompanion<OfflineResponse> {
  final Value<String> id;
  final Value<String> formId;
  final Value<String> commitId;
  final Value<String> answersJson;
  final Value<String> status;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const OfflineResponsesCompanion({
    this.id = const Value.absent(),
    this.formId = const Value.absent(),
    this.commitId = const Value.absent(),
    this.answersJson = const Value.absent(),
    this.status = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OfflineResponsesCompanion.insert({
    required String id,
    required String formId,
    required String commitId,
    required String answersJson,
    required String status,
    required DateTime createdAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       formId = Value(formId),
       commitId = Value(commitId),
       answersJson = Value(answersJson),
       status = Value(status),
       createdAt = Value(createdAt);
  static Insertable<OfflineResponse> custom({
    Expression<String>? id,
    Expression<String>? formId,
    Expression<String>? commitId,
    Expression<String>? answersJson,
    Expression<String>? status,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (formId != null) 'form_id': formId,
      if (commitId != null) 'commit_id': commitId,
      if (answersJson != null) 'answers_json': answersJson,
      if (status != null) 'status': status,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OfflineResponsesCompanion copyWith({
    Value<String>? id,
    Value<String>? formId,
    Value<String>? commitId,
    Value<String>? answersJson,
    Value<String>? status,
    Value<DateTime>? createdAt,
    Value<int>? rowid,
  }) {
    return OfflineResponsesCompanion(
      id: id ?? this.id,
      formId: formId ?? this.formId,
      commitId: commitId ?? this.commitId,
      answersJson: answersJson ?? this.answersJson,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (formId.present) {
      map['form_id'] = Variable<String>(formId.value);
    }
    if (commitId.present) {
      map['commit_id'] = Variable<String>(commitId.value);
    }
    if (answersJson.present) {
      map['answers_json'] = Variable<String>(answersJson.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OfflineResponsesCompanion(')
          ..write('id: $id, ')
          ..write('formId: $formId, ')
          ..write('commitId: $commitId, ')
          ..write('answersJson: $answersJson, ')
          ..write('status: $status, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $TombstonesTable extends Tombstones
    with TableInfo<$TombstonesTable, Tombstone> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TombstonesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _entityTypeMeta = const VerificationMeta(
    'entityType',
  );
  @override
  late final GeneratedColumn<String> entityType = GeneratedColumn<String>(
    'entity_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _entityIdMeta = const VerificationMeta(
    'entityId',
  );
  @override
  late final GeneratedColumn<String> entityId = GeneratedColumn<String>(
    'entity_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deletedAtMeta = const VerificationMeta(
    'deletedAt',
  );
  @override
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [entityType, entityId, deletedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'tombstones';
  @override
  VerificationContext validateIntegrity(
    Insertable<Tombstone> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('entity_type')) {
      context.handle(
        _entityTypeMeta,
        entityType.isAcceptableOrUnknown(data['entity_type']!, _entityTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_entityTypeMeta);
    }
    if (data.containsKey('entity_id')) {
      context.handle(
        _entityIdMeta,
        entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta),
      );
    } else if (isInserting) {
      context.missing(_entityIdMeta);
    }
    if (data.containsKey('deleted_at')) {
      context.handle(
        _deletedAtMeta,
        deletedAt.isAcceptableOrUnknown(data['deleted_at']!, _deletedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_deletedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {entityType, entityId};
  @override
  Tombstone map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Tombstone(
      entityType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}entity_type'],
      )!,
      entityId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}entity_id'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      )!,
    );
  }

  @override
  $TombstonesTable createAlias(String alias) {
    return $TombstonesTable(attachedDatabase, alias);
  }
}

class Tombstone extends DataClass implements Insertable<Tombstone> {
  final String entityType;
  final String entityId;
  final DateTime deletedAt;
  const Tombstone({
    required this.entityType,
    required this.entityId,
    required this.deletedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['entity_type'] = Variable<String>(entityType);
    map['entity_id'] = Variable<String>(entityId);
    map['deleted_at'] = Variable<DateTime>(deletedAt);
    return map;
  }

  TombstonesCompanion toCompanion(bool nullToAbsent) {
    return TombstonesCompanion(
      entityType: Value(entityType),
      entityId: Value(entityId),
      deletedAt: Value(deletedAt),
    );
  }

  factory Tombstone.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Tombstone(
      entityType: serializer.fromJson<String>(json['entityType']),
      entityId: serializer.fromJson<String>(json['entityId']),
      deletedAt: serializer.fromJson<DateTime>(json['deletedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'entityType': serializer.toJson<String>(entityType),
      'entityId': serializer.toJson<String>(entityId),
      'deletedAt': serializer.toJson<DateTime>(deletedAt),
    };
  }

  Tombstone copyWith({
    String? entityType,
    String? entityId,
    DateTime? deletedAt,
  }) => Tombstone(
    entityType: entityType ?? this.entityType,
    entityId: entityId ?? this.entityId,
    deletedAt: deletedAt ?? this.deletedAt,
  );
  Tombstone copyWithCompanion(TombstonesCompanion data) {
    return Tombstone(
      entityType: data.entityType.present
          ? data.entityType.value
          : this.entityType,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Tombstone(')
          ..write('entityType: $entityType, ')
          ..write('entityId: $entityId, ')
          ..write('deletedAt: $deletedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(entityType, entityId, deletedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Tombstone &&
          other.entityType == this.entityType &&
          other.entityId == this.entityId &&
          other.deletedAt == this.deletedAt);
}

class TombstonesCompanion extends UpdateCompanion<Tombstone> {
  final Value<String> entityType;
  final Value<String> entityId;
  final Value<DateTime> deletedAt;
  final Value<int> rowid;
  const TombstonesCompanion({
    this.entityType = const Value.absent(),
    this.entityId = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  TombstonesCompanion.insert({
    required String entityType,
    required String entityId,
    required DateTime deletedAt,
    this.rowid = const Value.absent(),
  }) : entityType = Value(entityType),
       entityId = Value(entityId),
       deletedAt = Value(deletedAt);
  static Insertable<Tombstone> custom({
    Expression<String>? entityType,
    Expression<String>? entityId,
    Expression<DateTime>? deletedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (entityType != null) 'entity_type': entityType,
      if (entityId != null) 'entity_id': entityId,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  TombstonesCompanion copyWith({
    Value<String>? entityType,
    Value<String>? entityId,
    Value<DateTime>? deletedAt,
    Value<int>? rowid,
  }) {
    return TombstonesCompanion(
      entityType: entityType ?? this.entityType,
      entityId: entityId ?? this.entityId,
      deletedAt: deletedAt ?? this.deletedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (entityType.present) {
      map['entity_type'] = Variable<String>(entityType.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<String>(entityId.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TombstonesCompanion(')
          ..write('entityType: $entityType, ')
          ..write('entityId: $entityId, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$OfflineDatabase extends GeneratedDatabase {
  _$OfflineDatabase(QueryExecutor e) : super(e);
  $OfflineDatabaseManager get managers => $OfflineDatabaseManager(this);
  late final $FormsCacheTable formsCache = $FormsCacheTable(this);
  late final $OfflineResponsesTable offlineResponses = $OfflineResponsesTable(
    this,
  );
  late final $TombstonesTable tombstones = $TombstonesTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    formsCache,
    offlineResponses,
    tombstones,
  ];
}

typedef $$FormsCacheTableCreateCompanionBuilder =
    FormsCacheCompanion Function({
      required String id,
      required String orgId,
      required String projectId,
      required String name,
      required String description,
      required String schemaJson,
      Value<DateTime?> lastSyncedAt,
      Value<int> rowid,
    });
typedef $$FormsCacheTableUpdateCompanionBuilder =
    FormsCacheCompanion Function({
      Value<String> id,
      Value<String> orgId,
      Value<String> projectId,
      Value<String> name,
      Value<String> description,
      Value<String> schemaJson,
      Value<DateTime?> lastSyncedAt,
      Value<int> rowid,
    });

class $$FormsCacheTableFilterComposer
    extends Composer<_$OfflineDatabase, $FormsCacheTable> {
  $$FormsCacheTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get orgId => $composableBuilder(
    column: $table.orgId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get description => $composableBuilder(
    column: $table.description,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$FormsCacheTableOrderingComposer
    extends Composer<_$OfflineDatabase, $FormsCacheTable> {
  $$FormsCacheTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get orgId => $composableBuilder(
    column: $table.orgId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get description => $composableBuilder(
    column: $table.description,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$FormsCacheTableAnnotationComposer
    extends Composer<_$OfflineDatabase, $FormsCacheTable> {
  $$FormsCacheTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get orgId =>
      $composableBuilder(column: $table.orgId, builder: (column) => column);

  GeneratedColumn<String> get projectId =>
      $composableBuilder(column: $table.projectId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
    column: $table.description,
    builder: (column) => column,
  );

  GeneratedColumn<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => column,
  );
}

class $$FormsCacheTableTableManager
    extends
        RootTableManager<
          _$OfflineDatabase,
          $FormsCacheTable,
          FormsCacheData,
          $$FormsCacheTableFilterComposer,
          $$FormsCacheTableOrderingComposer,
          $$FormsCacheTableAnnotationComposer,
          $$FormsCacheTableCreateCompanionBuilder,
          $$FormsCacheTableUpdateCompanionBuilder,
          (
            FormsCacheData,
            BaseReferences<_$OfflineDatabase, $FormsCacheTable, FormsCacheData>,
          ),
          FormsCacheData,
          PrefetchHooks Function()
        > {
  $$FormsCacheTableTableManager(_$OfflineDatabase db, $FormsCacheTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$FormsCacheTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$FormsCacheTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$FormsCacheTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> orgId = const Value.absent(),
                Value<String> projectId = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<String> description = const Value.absent(),
                Value<String> schemaJson = const Value.absent(),
                Value<DateTime?> lastSyncedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => FormsCacheCompanion(
                id: id,
                orgId: orgId,
                projectId: projectId,
                name: name,
                description: description,
                schemaJson: schemaJson,
                lastSyncedAt: lastSyncedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String orgId,
                required String projectId,
                required String name,
                required String description,
                required String schemaJson,
                Value<DateTime?> lastSyncedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => FormsCacheCompanion.insert(
                id: id,
                orgId: orgId,
                projectId: projectId,
                name: name,
                description: description,
                schemaJson: schemaJson,
                lastSyncedAt: lastSyncedAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$FormsCacheTableProcessedTableManager =
    ProcessedTableManager<
      _$OfflineDatabase,
      $FormsCacheTable,
      FormsCacheData,
      $$FormsCacheTableFilterComposer,
      $$FormsCacheTableOrderingComposer,
      $$FormsCacheTableAnnotationComposer,
      $$FormsCacheTableCreateCompanionBuilder,
      $$FormsCacheTableUpdateCompanionBuilder,
      (
        FormsCacheData,
        BaseReferences<_$OfflineDatabase, $FormsCacheTable, FormsCacheData>,
      ),
      FormsCacheData,
      PrefetchHooks Function()
    >;
typedef $$OfflineResponsesTableCreateCompanionBuilder =
    OfflineResponsesCompanion Function({
      required String id,
      required String formId,
      required String commitId,
      required String answersJson,
      required String status,
      required DateTime createdAt,
      Value<int> rowid,
    });
typedef $$OfflineResponsesTableUpdateCompanionBuilder =
    OfflineResponsesCompanion Function({
      Value<String> id,
      Value<String> formId,
      Value<String> commitId,
      Value<String> answersJson,
      Value<String> status,
      Value<DateTime> createdAt,
      Value<int> rowid,
    });

class $$OfflineResponsesTableFilterComposer
    extends Composer<_$OfflineDatabase, $OfflineResponsesTable> {
  $$OfflineResponsesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get commitId => $composableBuilder(
    column: $table.commitId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$OfflineResponsesTableOrderingComposer
    extends Composer<_$OfflineDatabase, $OfflineResponsesTable> {
  $$OfflineResponsesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get commitId => $composableBuilder(
    column: $table.commitId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$OfflineResponsesTableAnnotationComposer
    extends Composer<_$OfflineDatabase, $OfflineResponsesTable> {
  $$OfflineResponsesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get formId =>
      $composableBuilder(column: $table.formId, builder: (column) => column);

  GeneratedColumn<String> get commitId =>
      $composableBuilder(column: $table.commitId, builder: (column) => column);

  GeneratedColumn<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => column,
  );

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$OfflineResponsesTableTableManager
    extends
        RootTableManager<
          _$OfflineDatabase,
          $OfflineResponsesTable,
          OfflineResponse,
          $$OfflineResponsesTableFilterComposer,
          $$OfflineResponsesTableOrderingComposer,
          $$OfflineResponsesTableAnnotationComposer,
          $$OfflineResponsesTableCreateCompanionBuilder,
          $$OfflineResponsesTableUpdateCompanionBuilder,
          (
            OfflineResponse,
            BaseReferences<
              _$OfflineDatabase,
              $OfflineResponsesTable,
              OfflineResponse
            >,
          ),
          OfflineResponse,
          PrefetchHooks Function()
        > {
  $$OfflineResponsesTableTableManager(
    _$OfflineDatabase db,
    $OfflineResponsesTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$OfflineResponsesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$OfflineResponsesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$OfflineResponsesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> formId = const Value.absent(),
                Value<String> commitId = const Value.absent(),
                Value<String> answersJson = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => OfflineResponsesCompanion(
                id: id,
                formId: formId,
                commitId: commitId,
                answersJson: answersJson,
                status: status,
                createdAt: createdAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String formId,
                required String commitId,
                required String answersJson,
                required String status,
                required DateTime createdAt,
                Value<int> rowid = const Value.absent(),
              }) => OfflineResponsesCompanion.insert(
                id: id,
                formId: formId,
                commitId: commitId,
                answersJson: answersJson,
                status: status,
                createdAt: createdAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$OfflineResponsesTableProcessedTableManager =
    ProcessedTableManager<
      _$OfflineDatabase,
      $OfflineResponsesTable,
      OfflineResponse,
      $$OfflineResponsesTableFilterComposer,
      $$OfflineResponsesTableOrderingComposer,
      $$OfflineResponsesTableAnnotationComposer,
      $$OfflineResponsesTableCreateCompanionBuilder,
      $$OfflineResponsesTableUpdateCompanionBuilder,
      (
        OfflineResponse,
        BaseReferences<
          _$OfflineDatabase,
          $OfflineResponsesTable,
          OfflineResponse
        >,
      ),
      OfflineResponse,
      PrefetchHooks Function()
    >;
typedef $$TombstonesTableCreateCompanionBuilder =
    TombstonesCompanion Function({
      required String entityType,
      required String entityId,
      required DateTime deletedAt,
      Value<int> rowid,
    });
typedef $$TombstonesTableUpdateCompanionBuilder =
    TombstonesCompanion Function({
      Value<String> entityType,
      Value<String> entityId,
      Value<DateTime> deletedAt,
      Value<int> rowid,
    });

class $$TombstonesTableFilterComposer
    extends Composer<_$OfflineDatabase, $TombstonesTable> {
  $$TombstonesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get entityId => $composableBuilder(
    column: $table.entityId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get deletedAt => $composableBuilder(
    column: $table.deletedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$TombstonesTableOrderingComposer
    extends Composer<_$OfflineDatabase, $TombstonesTable> {
  $$TombstonesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get entityId => $composableBuilder(
    column: $table.entityId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get deletedAt => $composableBuilder(
    column: $table.deletedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$TombstonesTableAnnotationComposer
    extends Composer<_$OfflineDatabase, $TombstonesTable> {
  $$TombstonesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<DateTime> get deletedAt =>
      $composableBuilder(column: $table.deletedAt, builder: (column) => column);
}

class $$TombstonesTableTableManager
    extends
        RootTableManager<
          _$OfflineDatabase,
          $TombstonesTable,
          Tombstone,
          $$TombstonesTableFilterComposer,
          $$TombstonesTableOrderingComposer,
          $$TombstonesTableAnnotationComposer,
          $$TombstonesTableCreateCompanionBuilder,
          $$TombstonesTableUpdateCompanionBuilder,
          (
            Tombstone,
            BaseReferences<_$OfflineDatabase, $TombstonesTable, Tombstone>,
          ),
          Tombstone,
          PrefetchHooks Function()
        > {
  $$TombstonesTableTableManager(_$OfflineDatabase db, $TombstonesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TombstonesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TombstonesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TombstonesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> entityType = const Value.absent(),
                Value<String> entityId = const Value.absent(),
                Value<DateTime> deletedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => TombstonesCompanion(
                entityType: entityType,
                entityId: entityId,
                deletedAt: deletedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String entityType,
                required String entityId,
                required DateTime deletedAt,
                Value<int> rowid = const Value.absent(),
              }) => TombstonesCompanion.insert(
                entityType: entityType,
                entityId: entityId,
                deletedAt: deletedAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$TombstonesTableProcessedTableManager =
    ProcessedTableManager<
      _$OfflineDatabase,
      $TombstonesTable,
      Tombstone,
      $$TombstonesTableFilterComposer,
      $$TombstonesTableOrderingComposer,
      $$TombstonesTableAnnotationComposer,
      $$TombstonesTableCreateCompanionBuilder,
      $$TombstonesTableUpdateCompanionBuilder,
      (
        Tombstone,
        BaseReferences<_$OfflineDatabase, $TombstonesTable, Tombstone>,
      ),
      Tombstone,
      PrefetchHooks Function()
    >;

class $OfflineDatabaseManager {
  final _$OfflineDatabase _db;
  $OfflineDatabaseManager(this._db);
  $$FormsCacheTableTableManager get formsCache =>
      $$FormsCacheTableTableManager(_db, _db.formsCache);
  $$OfflineResponsesTableTableManager get offlineResponses =>
      $$OfflineResponsesTableTableManager(_db, _db.offlineResponses);
  $$TombstonesTableTableManager get tombstones =>
      $$TombstonesTableTableManager(_db, _db.tombstones);
}
