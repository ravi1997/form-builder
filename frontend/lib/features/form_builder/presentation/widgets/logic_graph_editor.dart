import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/form_builder_provider.dart';
import '../../providers/logic_validator.dart';
import '../../../../shared/json_ui_engine/models/visibility_rule.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';

class SectionLogicEditor extends ConsumerStatefulWidget {
  final FormSection section;
  const SectionLogicEditor({super.key, required this.section});

  @override
  ConsumerState<SectionLogicEditor> createState() => _SectionLogicEditorState();
}

class _SectionLogicEditorState extends ConsumerState<SectionLogicEditor> {
  bool _isGraphView = false;
  late TextEditingController _visibilityController;
  late TextEditingController _skipToController;

  @override
  void initState() {
    super.initState();
    _visibilityController = TextEditingController(text: widget.section.visibilityRule ?? '');
    _skipToController = TextEditingController(text: widget.section.skipToSectionId ?? '');
  }

  @override
  void didUpdateWidget(covariant SectionLogicEditor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.section.visibilityRule != _visibilityController.text) {
      _visibilityController.text = widget.section.visibilityRule ?? '';
    }
    if (widget.section.skipToSectionId != _skipToController.text) {
      _skipToController.text = widget.section.skipToSectionId ?? '';
    }
  }

  @override
  void dispose() {
    _visibilityController.dispose();
    _skipToController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final theme = Theme.of(context);

    // Filter validation issues related to this section
    final sectionIssues = builderState.logicIssues.where((issue) {
      return issue.relatedNodeIds.contains(widget.section.id);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                'Section Logic',
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
            ),
            SegmentedButton<bool>(
              showSelectedIcon: false,
              segments: const [
                ButtonSegment(
                  value: false,
                  label: Text('List', style: TextStyle(fontSize: 12)),
                ),
                ButtonSegment(
                  value: true,
                  label: Text('Graph', style: TextStyle(fontSize: 12)),
                ),
              ],
              selected: {_isGraphView},
              onSelectionChanged: (val) {
                setState(() {
                  _isGraphView = val.first;
                });
              },
            ),
          ],
        ),
        SizedBox(height: AppSpacing.md),
        if (sectionIssues.isNotEmpty) ...[
          _buildIssuesList(sectionIssues),
          SizedBox(height: AppSpacing.md),
        ],
        _isGraphView
            ? _buildGraphPreview(context, builderState)
            : _buildListEditor(context),
      ],
    );
  }

  Widget _buildIssuesList(List<LogicValidationIssue> issues) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.stateError.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.stateError.withValues(alpha: 0.3)),
      ),
      padding: EdgeInsets.all(AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: AppColors.stateError, size: 16),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'Logic Warnings Detected',
                  style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.stateError, fontSize: 13),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ...issues.map((issue) {
            final color = issue.severity == 'error'
                ? AppColors.stateError
                : (issue.severity == 'warning' ? Colors.orange : Colors.blue);
            return Padding(
              key: ValueKey('issue_${issue.id}'),
              padding: const EdgeInsets.symmetric(vertical: 2.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('• ', style: TextStyle(color: color, fontWeight: FontWeight.bold)),
                  Expanded(
                    child: Text(
                      issue.message,
                      style: TextStyle(fontSize: 11, color: color),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildListEditor(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Use visibility rules and skip targets to shape flow.',
          style: TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
        SizedBox(height: AppSpacing.md),
        TextField(
          key: const ValueKey('logic-visibility-input'),
          controller: _visibilityController,
          decoration: const InputDecoration(
            labelText: 'Visibility Rule Summary',
            hintText: 'show when q_dropdown == yes',
            border: OutlineInputBorder(),
          ),
          minLines: 2,
          maxLines: 4,
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSection(
                  widget.section.id,
                  visibilityRule: val.isEmpty ? null : val,
                );
          },
        ),
        SizedBox(height: AppSpacing.md),
        TextField(
          key: const ValueKey('logic-skipto-input'),
          controller: _skipToController,
          decoration: const InputDecoration(
            labelText: 'Skip Target Section ID',
            hintText: 'sec_2',
            border: OutlineInputBorder(),
          ),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSection(
                  widget.section.id,
                  skipToSectionId: val.isEmpty ? null : val,
                );
          },
        ),
      ],
    );
  }

  Widget _buildGraphPreview(BuildContext context, FormBuilderState builderState) {
    return Container(
      height: 180,
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.surfaceCanvas,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.builderDivider),
      ),
      child: Stack(
        children: [
          const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.account_tree_outlined, size: 36, color: AppColors.textMuted),
                SizedBox(height: 6),
                Text(
                  'Visual Logic Graph',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          Positioned(
            right: 8,
            bottom: 8,
            child: FilledButton.icon(
              key: const ValueKey('btn-open-logic-canvas'),
              onPressed: () {
                showGeneralDialog(
                  context: context,
                  barrierDismissible: true,
                  barrierLabel: 'Logic Canvas',
                  pageBuilder: (context, anim1, anim2) {
                    return InteractiveLogicCanvas(initialSectionId: widget.section.id);
                  },
                );
              },
              icon: const Icon(Icons.fullscreen, size: 16),
              label: const Text('Open Canvas', style: TextStyle(fontSize: 11)),
              style: FilledButton.styleFrom(
                visualDensity: VisualDensity.compact,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class InteractiveLogicCanvas extends ConsumerStatefulWidget {
  final String initialSectionId;
  const InteractiveLogicCanvas({super.key, required this.initialSectionId});

  @override
  ConsumerState<InteractiveLogicCanvas> createState() => _InteractiveLogicCanvasState();
}

class _InteractiveLogicCanvasState extends ConsumerState<InteractiveLogicCanvas> {
  String _filterType = 'all'; // 'all', 'visibility', 'skip'
  String? _selectedNodeId;
  final Map<String, Offset> _nodeOffsets = {};

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final theme = Theme.of(context);

    // Compute nodes & edges
    final nodes = <LogicNode>[];
    final edges = <LogicEdge>[];

    final allQuestionIds = <String>{};
    final questionMap = <String, FormQuestion>{};
    final allSectionIds = <String>{};
    final sectionMap = <String, FormSection>{};

    for (final sec in builderState.sections) {
      allSectionIds.add(sec.id);
      sectionMap[sec.id] = sec;
      for (final sub in sec.subSections) {
        for (final q in sub.questions) {
          allQuestionIds.add(q.id);
          questionMap[q.id] = q;
        }
      }
    }

    // Generate Nodes
    for (final sec in builderState.sections) {
      if (_filterType == 'all' || _filterType == 'skip' || (sec.visibilityRule?.isNotEmpty ?? false)) {
        nodes.add(LogicNode(id: sec.id, label: sec.title, type: 'section'));
      }
    }
    for (final q in questionMap.values) {
      // Add questions if referenced in any visibility rule
      var isReferenced = false;
      for (final sec in builderState.sections) {
        if (sec.visibilityRule?.toLowerCase().contains(q.id.toLowerCase()) ?? false) {
          isReferenced = true;
        }
      }
      for (final question in questionMap.values) {
        for (final cond in question.visibilityRules.conditions) {
          if (cond is AnswerCondition && cond.fieldId == q.id) {
            isReferenced = true;
          }
        }
      }
      if (isReferenced && (_filterType == 'all' || _filterType == 'visibility')) {
        nodes.add(LogicNode(id: q.id, label: q.label, type: 'field'));
      }
    }

    // Generate Edges
    for (final sec in builderState.sections) {
      if (_filterType == 'all' || _filterType == 'visibility') {
        final rule = sec.visibilityRule ?? '';
        if (rule.isNotEmpty) {
          for (final qId in allQuestionIds) {
            if (rule.toLowerCase().contains(qId.toLowerCase())) {
              edges.add(LogicEdge(
                id: '${qId}_to_${sec.id}_vis',
                from: qId,
                to: sec.id,
                label: 'show when',
                type: 'visibility',
              ));
            }
          }
        }
      }

      if (_filterType == 'all' || _filterType == 'skip') {
        final skipTarget = sec.skipToSectionId ?? '';
        if (skipTarget.isNotEmpty) {
          edges.add(LogicEdge(
            id: '${sec.id}_to_${skipTarget}_skip',
            from: sec.id,
            to: skipTarget,
            label: 'skip to',
            type: 'skip',
          ));
        }
      }
    }

    for (final q in questionMap.values) {
      if (_filterType == 'all' || _filterType == 'visibility') {
        for (final cond in q.visibilityRules.conditions) {
          if (cond is AnswerCondition) {
            edges.add(LogicEdge(
              id: '${cond.fieldId}_to_${q.id}_vis',
              from: cond.fieldId,
              to: q.id,
              label: 'show when',
              type: 'visibility',
            ));
          }
        }
      }
    }

    // Initialize layout positions
    int sectionCount = 0;
    int fieldCount = 0;
    for (final node in nodes) {
      _nodeOffsets.putIfAbsent(node.id, () {
        if (node.type == 'section') {
          sectionCount++;
          return Offset(150.0 + (sectionCount * 220), 300.0);
        } else {
          fieldCount++;
          return Offset(150.0 + (fieldCount * 220), 100.0);
        }
      });
    }

    final activeIssueNodes = builderState.logicIssues.expand((i) => i.relatedNodeIds).toSet();

    return Material(
      color: AppColors.builderBackground,
      child: SafeArea(
        child: Column(
          children: [
            // Top Toolbar
            Container(
              padding: EdgeInsets.all(AppSpacing.md),
              decoration: const BoxDecoration(
                color: AppColors.surfaceCard,
                border: Border(bottom: BorderSide(color: AppColors.builderDivider)),
              ),
              child: Row(
                children: [
                  IconButton(
                    key: const ValueKey('btn-close-canvas'),
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                  SizedBox(width: AppSpacing.sm),
                  Text(
                    'Visual Logic Canvas',
                    style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const Spacer(),
                  // Filter dropdown
                  DropdownButton<String>(
                    value: _filterType,
                    items: const [
                      DropdownMenuItem(value: 'all', child: Text('All Rules')),
                      DropdownMenuItem(value: 'visibility', child: Text('Visibility Only')),
                      DropdownMenuItem(value: 'skip', child: Text('Skip Rules Only')),
                    ],
                    onChanged: (val) {
                      setState(() {
                        _filterType = val ?? 'all';
                      });
                    },
                  ),
                ],
              ),
            ),
            // Middle Split: Graph Canvas & Inspector
            Expanded(
              child: Row(
                children: [
                  // Graph Area
                  Expanded(
                    child: InteractiveViewer(
                      boundaryMargin: const EdgeInsets.all(1000),
                      minScale: 0.1,
                      maxScale: 2.0,
                      child: Stack(
                        children: [
                          // Custom Painter for Edges
                          Positioned.fill(
                            child: CustomPaint(
                              painter: GraphEdgePainter(
                                edges: edges,
                                nodeOffsets: _nodeOffsets,
                                activeIssueEdges: builderState.logicIssues,
                              ),
                            ),
                          ),
                          // Positioned nodes
                          ...nodes.map((node) {
                            final offset = _nodeOffsets[node.id] ?? Offset.zero;
                            final isSelected = _selectedNodeId == node.id;
                            final isErroneous = activeIssueNodes.contains(node.id);
                            return Positioned(
                              left: offset.dx,
                              top: offset.dy,
                              child: GestureDetector(
                                onPanUpdate: (details) {
                                  setState(() {
                                    _nodeOffsets[node.id] = offset + details.delta;
                                  });
                                },
                                onTap: () {
                                  setState(() {
                                    _selectedNodeId = node.id;
                                  });
                                },
                                child: Container(
                                  key: ValueKey('node_${node.id}'),
                                  width: 180,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: isSelected
                                        ? theme.colorScheme.primary.withValues(alpha: 0.1)
                                        : AppColors.surfaceCard,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: isErroneous
                                          ? AppColors.stateError
                                          : (isSelected ? theme.colorScheme.primary : AppColors.builderDivider),
                                      width: isSelected ? 2 : 1,
                                    ),
                                    boxShadow: const [
                                      BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 2)),
                                    ],
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Row(
                                        children: [
                                          Icon(
                                            node.type == 'section' ? Icons.dashboard : Icons.text_fields,
                                            size: 14,
                                            color: node.type == 'section' ? Colors.purple : Colors.blue,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            node.type.toUpperCase(),
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: node.type == 'section' ? Colors.purple : Colors.blue,
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        node.label,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        'ID: ${node.id}',
                                        style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          }),
                        ],
                      ),
                    ),
                  ),
                  // Inspector Panel (Side Panel)
                  Container(
                    width: 320,
                    decoration: const BoxDecoration(
                      color: AppColors.surfaceCard,
                      border: Border(left: BorderSide(color: AppColors.builderDivider)),
                    ),
                    padding: EdgeInsets.all(AppSpacing.md),
                    child: _buildInspector(context, builderState, sectionMap, questionMap),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInspector(
    BuildContext context,
    FormBuilderState builderState,
    Map<String, FormSection> sectionMap,
    Map<String, FormQuestion> questionMap,
  ) {
    if (_selectedNodeId == null) {
      return const Center(
        child: Text(
          'Select a node on the canvas to inspect or edit its logic rules.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
      );
    }

    final id = _selectedNodeId!;
    final isSection = sectionMap.containsKey(id);

    if (isSection) {
      final sec = sectionMap[id]!;
      return ListView(
        children: [
          Row(
            children: [
              const Icon(Icons.dashboard, color: Colors.purple, size: 18),
              const SizedBox(width: 6),
              const Text('Section Node', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const Divider(),
          SizedBox(height: AppSpacing.sm),
          Text('Title: ${sec.title}', style: const TextStyle(fontWeight: FontWeight.bold)),
          Text('ID: ${sec.id}', style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
          SizedBox(height: AppSpacing.lg),
          TextField(
            key: const ValueKey('canvas-visibility-input'),
            controller: TextEditingController(text: sec.visibilityRule ?? ''),
            decoration: const InputDecoration(
              labelText: 'Visibility Rule',
              hintText: 'show when q_dropdown == yes',
              border: OutlineInputBorder(),
            ),
            onChanged: (val) {
              ref.read(formBuilderProvider.notifier).updateSection(
                    sec.id,
                    visibilityRule: val.isEmpty ? null : val,
                  );
            },
          ),
          SizedBox(height: AppSpacing.md),
          TextField(
            key: const ValueKey('canvas-skipto-input'),
            controller: TextEditingController(text: sec.skipToSectionId ?? ''),
            decoration: const InputDecoration(
              labelText: 'Skip Target Section ID',
              hintText: 'sec_2',
              border: OutlineInputBorder(),
            ),
            onChanged: (val) {
              ref.read(formBuilderProvider.notifier).updateSection(
                    sec.id,
                    skipToSectionId: val.isEmpty ? null : val,
                  );
            },
          ),
        ],
      );
    } else {
      final q = questionMap[id]!;
      return ListView(
        children: [
          Row(
            children: [
              const Icon(Icons.text_fields, color: Colors.blue, size: 18),
              const SizedBox(width: 6),
              const Text('Field Node', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const Divider(),
          SizedBox(height: AppSpacing.sm),
          Text('Label: ${q.label}', style: const TextStyle(fontWeight: FontWeight.bold)),
          Text('ID: ${q.id}', style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
          SizedBox(height: AppSpacing.lg),
          SwitchListTile(
            title: const Text('Required'),
            value: q.required,
            onChanged: (val) {
              ref.read(formBuilderProvider.notifier).updateQuestion(q.id, required: val);
            },
          ),
        ],
      );
    }
  }
}

class GraphEdgePainter extends CustomPainter {
  final List<LogicEdge> edges;
  final Map<String, Offset> nodeOffsets;
  final List<LogicValidationIssue> activeIssueEdges;

  GraphEdgePainter({
    required this.edges,
    required this.nodeOffsets,
    required this.activeIssueEdges,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final edgeErrorNodes = activeIssueEdges.where((i) => i.severity == 'error').expand((i) => i.relatedNodeIds).toSet();
    final edgeWarningNodes = activeIssueEdges.where((i) => i.severity == 'warning').expand((i) => i.relatedNodeIds).toSet();

    for (final edge in edges) {
      final fromOffset = nodeOffsets[edge.from];
      final toOffset = nodeOffsets[edge.to];

      if (fromOffset != null && toOffset != null) {
        final start = fromOffset + const Offset(90, 30);
        final end = toOffset + const Offset(90, 30);

        final isError = edgeErrorNodes.contains(edge.from) && edgeErrorNodes.contains(edge.to);
        final isWarning = edgeWarningNodes.contains(edge.from) && edgeWarningNodes.contains(edge.to);

        final paint = Paint()
          ..strokeWidth = (isError || isWarning) ? 2.5 : 1.5
          ..color = isError
              ? AppColors.stateError
              : (isWarning ? Colors.orange : AppColors.textMuted.withValues(alpha: 0.5))
          ..style = PaintingStyle.stroke;

        canvas.drawLine(start, end, paint);

        final arrowPaint = Paint()
          ..color = paint.color
          ..style = PaintingStyle.fill;
        final direction = (end - start).direction;
        final arrowLength = 8.0;
        final arrowAngle = 0.4;

        final tip = end - Offset.fromDirection(direction, 35);
        final p1 = tip - Offset.fromDirection(direction - arrowAngle, arrowLength);
        final p2 = tip - Offset.fromDirection(direction + arrowAngle, arrowLength);

        final path = Path()
          ..moveTo(tip.dx, tip.dy)
          ..lineTo(p1.dx, p1.dy)
          ..lineTo(p2.dx, p2.dy)
          ..close();

        canvas.drawPath(path, arrowPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
