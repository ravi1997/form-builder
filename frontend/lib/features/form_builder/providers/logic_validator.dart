import 'form_builder_provider.dart';
import '../../../shared/json_ui_engine/models/visibility_rule.dart';

class LogicNode {
  final String id;
  final String label;
  final String type; // 'field', 'section'
  double x;
  double y;

  LogicNode({
    required this.id,
    required this.label,
    required this.type,
    this.x = 0.0,
    this.y = 0.0,
  });
}

class LogicEdge {
  final String id;
  final String from;
  final String to;
  final String label; // e.g. "show when == yes"
  final String type; // 'visibility', 'skip'

  LogicEdge({
    required this.id,
    required this.from,
    required this.to,
    this.label = '',
    required this.type,
  });
}

class LogicValidationIssue {
  final String id;
  final String message;
  final String severity; // 'error', 'warning', 'info'
  final List<String> relatedNodeIds;

  LogicValidationIssue({
    required this.id,
    required this.message,
    required this.severity,
    required this.relatedNodeIds,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'message': message,
      'severity': severity,
      'relatedNodeIds': relatedNodeIds,
    };
  }

  factory LogicValidationIssue.fromJson(Map<String, dynamic> json) {
    return LogicValidationIssue(
      id: json['id'] ?? '',
      message: json['message'] ?? '',
      severity: json['severity'] ?? 'warning',
      relatedNodeIds: List<String>.from(json['relatedNodeIds'] ?? const []),
    );
  }
}

class LogicGraphValidator {
  static List<LogicValidationIssue> validate(FormBuilderState state) {
    final List<LogicValidationIssue> issues = [];

    // Gather all questions and sections IDs
    final allQuestionIds = <String>{};
    final questionMap = <String, FormQuestion>{};
    final questionToSection = <String, String>{};
    final allSectionIds = <String>{};
    final sectionMap = <String, FormSection>{};

    for (final sec in state.sections) {
      allSectionIds.add(sec.id);
      sectionMap[sec.id] = sec;
      for (final sub in sec.subSections) {
        for (final q in sub.questions) {
          allQuestionIds.add(q.id);
          questionMap[q.id] = q;
          questionToSection[q.id] = sec.id;
        }
      }
    }

    // Build dependency graph
    // adj[A] = list of nodes that depend on A (i.e. A -> B means B depends on A)
    final Map<String, Set<String>> adj = {};
    final List<LogicEdge> edges = [];

    void addEdge(String from, String to, String label, String type) {
      adj.putIfAbsent(from, () => {}).add(to);
      edges.add(LogicEdge(
        id: '${from}_to_${to}_${type}',
        from: from,
        to: to,
        label: label,
        type: type,
      ));
    }

    // Parse section visibility rules
    for (final sec in state.sections) {
      final rule = sec.visibilityRule ?? '';
      if (rule.isNotEmpty) {
        final referencedQs = _findReferencedQuestions(rule, allQuestionIds);
        for (final qId in referencedQs) {
          addEdge(qId, sec.id, 'Controls visibility of section', 'visibility');

          // Contradiction check: Section visibility depends on its own question
          if (questionToSection[qId] == sec.id) {
            issues.add(LogicValidationIssue(
              id: 'self_dep_${sec.id}_$qId',
              message: 'Self-contradiction: Section "${sec.title}" visibility depends on its own field "${questionMap[qId]?.label ?? qId}". The field will be inaccessible when the section is hidden.',
              severity: 'warning',
              relatedNodeIds: [sec.id, qId],
            ));
          }
        }
      }

      // Section skip logic
      final skipTarget = sec.skipToSectionId ?? '';
      if (skipTarget.isNotEmpty) {
        addEdge(sec.id, skipTarget, 'Skips to', 'skip');
        if (!allSectionIds.contains(skipTarget)) {
          issues.add(LogicValidationIssue(
            id: 'invalid_skip_${sec.id}',
            message: 'Unreachable skip target: Section "${sec.title}" skips to non-existent section "$skipTarget".',
            severity: 'info',
            relatedNodeIds: [sec.id],
          ));
        }
      }
    }

    // Parse question visibility rules
    for (final q in questionMap.values) {
      for (final cond in q.visibilityRules.conditions) {
        if (cond is AnswerCondition) {
          addEdge(cond.fieldId, q.id, 'Controls visibility of field', 'visibility');
        }
      }
    }

    // Cycle detection using DFS
    final visited = <String, int>{}; // 0 = unvisited, 1 = visiting, 2 = visited
    final parent = <String, String>{};

    void dfs(String node) {
      visited[node] = 1;
      final neighbors = adj[node] ?? {};
      for (final next in neighbors) {
        if (visited[next] == 1) {
          // Cycle found! Trace it back
          final cycle = <String>[next];
          var curr = node;
          while (curr != next && curr.isNotEmpty) {
            cycle.add(curr);
            curr = parent[curr] ?? '';
          }
          cycle.add(next);
          final cyclePath = cycle.reversed.map((n) {
            if (questionMap.containsKey(n)) {
              return 'Field "${questionMap[n]!.label}"';
            } else if (sectionMap.containsKey(n)) {
              return 'Section "${sectionMap[n]!.title}"';
            }
            return n;
          }).join(' -> ');

          issues.add(LogicValidationIssue(
            id: 'cycle_${cycle.join("_")}',
            message: 'Circular logic loop detected: $cyclePath. This will block form progression or freeze the UI.',
            severity: 'error',
            relatedNodeIds: cycle,
          ));
        } else if ((visited[next] ?? 0) == 0) {
          parent[next] = node;
          dfs(next);
        }
      }
      visited[node] = 2;
    }

    // Run DFS from all nodes
    final allNodes = {...allQuestionIds, ...allSectionIds};
    for (final node in allNodes) {
      if ((visited[node] ?? 0) == 0) {
        dfs(node);
      }
    }

    return issues;
  }

  static Set<String> _findReferencedQuestions(String rule, Set<String> allQuestionIds) {
    final result = <String>{};
    final cleanRule = rule.toLowerCase();
    for (final qId in allQuestionIds) {
      if (cleanRule.contains(qId.toLowerCase())) {
        result.add(qId);
      }
    }
    return result;
  }
}
