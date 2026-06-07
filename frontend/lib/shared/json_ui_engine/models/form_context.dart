class FormContext {
  final String userRole;
  final List<String> userGroupIds;
  final String orgId;

  const FormContext({
    required this.userRole,
    required this.userGroupIds,
    required this.orgId,
  });

  factory FormContext.fromJson(Map<String, dynamic> json) {
    return FormContext(
      userRole: json['userRole'] ?? json['user_role'] ?? '',
      userGroupIds: json['userGroupIds'] != null ? List<String>.from(json['userGroupIds']) : (json['user_group_ids'] != null ? List<String>.from(json['user_group_ids']) : const []),
      orgId: json['orgId'] ?? json['org_id'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'userRole': userRole,
      'userGroupIds': userGroupIds,
      'orgId': orgId,
    };
  }
}
