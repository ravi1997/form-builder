class AnswerValue {
  final dynamic value;
  final String displayValue;
  final List<String>? fileIds;
  final DateTime? answeredAt;
  final int? iterationIndex;

  const AnswerValue({
    required this.value,
    required this.displayValue,
    this.fileIds,
    this.answeredAt,
    this.iterationIndex,
  });

  factory AnswerValue.empty() => const AnswerValue(value: null, displayValue: '');

  factory AnswerValue.fromJson(Map<String, dynamic> json) {
    return AnswerValue(
      value: json['value'],
      displayValue: json['display_value'] ?? json['displayValue'] ?? '',
      fileIds: json['file_ids'] != null ? List<String>.from(json['file_ids']) : (json['fileIds'] != null ? List<String>.from(json['fileIds']) : null),
      answeredAt: json['answered_at'] != null ? DateTime.parse(json['answered_at']) : (json['answeredAt'] != null ? DateTime.parse(json['answeredAt']) : null),
      iterationIndex: json['iteration_index'] ?? json['iterationIndex'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'value': value,
      'display_value': displayValue,
      'file_ids': fileIds,
      'answered_at': answeredAt?.toIso8601String(),
      'iteration_index': iterationIndex,
    };
  }

  AnswerValue copyWith({
    dynamic value,
    String? displayValue,
    List<String>? fileIds,
    DateTime? answeredAt,
    int? iterationIndex,
  }) {
    return AnswerValue(
      value: value ?? this.value,
      displayValue: displayValue ?? this.displayValue,
      fileIds: fileIds ?? this.fileIds,
      answeredAt: answeredAt ?? this.answeredAt,
      iterationIndex: iterationIndex ?? this.iterationIndex,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AnswerValue &&
          runtimeType == other.runtimeType &&
          value == other.value &&
          displayValue == other.displayValue &&
          fileIds == other.fileIds &&
          answeredAt == other.answeredAt &&
          iterationIndex == other.iterationIndex;

  @override
  int get hashCode =>
      value.hashCode ^
      displayValue.hashCode ^
      fileIds.hashCode ^
      answeredAt.hashCode ^
      iterationIndex.hashCode;
}
