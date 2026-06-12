import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../providers/form_builder_provider.dart';

Color _parseHexColor(String hex, Color fallback) {
  try {
    final cleanHex = hex.trim().replaceAll('#', '');
    if (cleanHex.length == 6) {
      return Color(int.parse('FF$cleanHex', radix: 16));
    } else if (cleanHex.length == 8) {
      return Color(int.parse(cleanHex, radix: 16));
    }
  } catch (_) {}
  return fallback;
}

class BuilderCanvas extends ConsumerStatefulWidget {
  final String? activeSubSectionId;
  final void Function(String) onSubSectionActivated;

  const BuilderCanvas({
    super.key,
    required this.activeSubSectionId,
    required this.onSubSectionActivated,
  });

  @override
  ConsumerState<BuilderCanvas> createState() => _BuilderCanvasState();
}

class _BuilderCanvasState extends ConsumerState<BuilderCanvas> {
  String? _hoveredTargetId;

  TextStyle? _applyFont(TextStyle? style, String fontFamily) {
    if (style == null) return null;
    return style.copyWith(fontFamily: fontFamily);
  }

  bool _evaluateVisibilityRule(String rule, Map<String, dynamic> answers) {
    if (rule.isEmpty) return true;
    try {
      final clean = rule.toLowerCase().replaceAll('show when', '').trim();
      if (clean.contains('==')) {
        final parts = clean.split('==');
        final key = parts[0].trim();
        final expected = parts[1].trim().replaceAll('"', '').replaceAll("'", "");
        final actual = answers[key]?.toString().toLowerCase() ?? '';
        return actual == expected;
      } else if (clean.contains('!=')) {
        final parts = clean.split('!=');
        final key = parts[0].trim();
        final expected = parts[1].trim().replaceAll('"', '').replaceAll("'", "");
        final actual = answers[key]?.toString().toLowerCase() ?? '';
        return actual != expected;
      } else if (clean.contains('>')) {
        final parts = clean.split('>');
        final key = parts[0].trim();
        final val = double.tryParse(parts[1].trim()) ?? 0.0;
        final actual = double.tryParse(answers[key]?.toString() ?? '') ?? 0.0;
        return actual > val;
      } else if (clean.contains('<')) {
        final parts = clean.split('<');
        final key = parts[0].trim();
        final val = double.tryParse(parts[1].trim()) ?? 0.0;
        final actual = double.tryParse(answers[key]?.toString() ?? '') ?? 0.0;
        return actual < val;
      }
    } catch (_) {}
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final playState = ref.watch(formPlayProvider);
    final theme = Theme.of(context);
    final canvasBg = _parseHexColor(builderState.style.backgroundColor, theme.colorScheme.surface);
    final canvasPrimary = _parseHexColor(builderState.style.primaryColor, theme.primaryColor);
    final fontFamily = builderState.style.fontFamily;
    final radius = builderState.style.borderRadius;

    return Container(
      key: const ValueKey('form-canvas-root'),
      decoration: AppSurfaceStyles.card(
        tint: canvasBg,
        radiusValue: radius,
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Toolbar / Mode selector
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Canvas',
                        style: _applyFont(theme.textTheme.titleLarge, fontFamily)?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        builderState.canvasMode == FormCanvasMode.play
                            ? 'Test form interactions, conditions, and validation live.'
                            : 'Compose sections, sub-sections, and questions in a single workspace.',
                        style: _applyFont(theme.textTheme.bodySmall, fontFamily)?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                SegmentedButton<FormCanvasMode>(
                  segments: const [
                    ButtonSegment(
                      value: FormCanvasMode.edit,
                      label: Text('Edit'),
                      icon: Icon(Icons.edit_outlined),
                    ),
                    ButtonSegment(
                      value: FormCanvasMode.play,
                      label: Text('Play'),
                      icon: Icon(Icons.play_arrow_outlined),
                    ),
                    ButtonSegment(
                      value: FormCanvasMode.split,
                      label: Text('Split'),
                      icon: Icon(Icons.splitscreen_outlined),
                    ),
                  ],
                  selected: {builderState.canvasMode},
                  onSelectionChanged: (val) {
                    ref.read(formBuilderProvider.notifier).setCanvasMode(val.first);
                  },
                ),
                if (builderState.canvasMode != FormCanvasMode.edit) ...[
                  const SizedBox(width: AppSpacing.sm),
                  IconButton(
                    tooltip: 'Reset Test State',
                    icon: const Icon(Icons.refresh),
                    onPressed: () {
                      ref.read(formPlayProvider.notifier).reset();
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Test response answers reset.')),
                      );
                    },
                  ),
                ],
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Container(height: 1, color: AppColors.builderDivider),
            const SizedBox(height: AppSpacing.md),

            // Main Canvas workspace
            Expanded(
              child: Builder(
                builder: (context) {
                  if (builderState.canvasMode == FormCanvasMode.edit) {
                    return _buildEditor(builderState, canvasBg, canvasPrimary, fontFamily, radius);
                  } else if (builderState.canvasMode == FormCanvasMode.play) {
                    return _buildPlay(builderState, playState, canvasBg, canvasPrimary, fontFamily, radius);
                  } else {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          child: _buildEditor(builderState, canvasBg, canvasPrimary, fontFamily, radius),
                        ),
                        const VerticalDivider(width: 16, thickness: 1, color: AppColors.builderDivider),
                        Expanded(
                          child: _buildPlay(builderState, playState, canvasBg, canvasPrimary, fontFamily, radius),
                        ),
                      ],
                    );
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEditor(FormBuilderState builderState, Color canvasBg, Color canvasPrimary, String fontFamily, double radius) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            FilledButton.icon(
              onPressed: () {
                ref.read(formBuilderProvider.notifier).addSection();
              },
              style: FilledButton.styleFrom(
                backgroundColor: canvasPrimary,
                foregroundColor: canvasBg.computeLuminance() > 0.5 ? Colors.white : Colors.black,
              ),
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Add section'),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Expanded(
          child: ListView.separated(
            padding: EdgeInsets.zero,
            itemCount: builderState.sections.length,
            separatorBuilder: (context, index) => const SizedBox(height: AppSpacing.md),
            itemBuilder: (context, sIndex) {
              final section = builderState.sections[sIndex];
              final isSelectedSec = builderState.selectedElementId == section.id;

              return Container(
                decoration: AppSurfaceStyles.card(
                  selected: isSelectedSec,
                  tint: isSelectedSec
                      ? canvasPrimary.withValues(alpha: 0.15)
                      : canvasBg.withValues(alpha: 0.9),
                  radiusValue: radius,
                ),
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Material(
                              color: Colors.transparent,
                              child: ListTile(
                                contentPadding: EdgeInsets.zero,
                                title: Text(
                                  section.title,
                                  style: _applyFont(theme.textTheme.titleMedium, fontFamily)
                                      ?.copyWith(fontWeight: FontWeight.w800),
                                ),
                                subtitle: Text(
                                  section.description.isNotEmpty ? section.description : 'No description',
                                  style: _applyFont(theme.textTheme.bodySmall, fontFamily)?.copyWith(
                                    color: AppColors.textMuted,
                                  ),
                                ),
                                onTap: () {
                                  ref.read(formBuilderProvider.notifier).selectElement(section.id);
                                },
                              ),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          FilledButton.tonalIcon(
                            onPressed: () {
                              ref.read(formBuilderProvider.notifier).addSubSection(section.id);
                            },
                            icon: const Icon(Icons.add, size: 18),
                            label: const Text('Sub-section'),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Container(height: 1, color: AppColors.builderDivider),
                      const SizedBox(height: AppSpacing.md),
                      ...section.subSections.map((subSec) {
                        final isSelectedSub = builderState.selectedElementId == subSec.id;
                        final isActiveSub = widget.activeSubSectionId == subSec.id;

                        return Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                          child: Container(
                            decoration: AppSurfaceStyles.insetCard(
                              selected: isSelectedSub || isActiveSub,
                              tint: isActiveSub
                                  ? canvasPrimary.withValues(alpha: 0.15)
                                  : canvasBg.withValues(alpha: 0.8),
                              radiusValue: radius * 0.8,
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Material(
                                          color: Colors.transparent,
                                          child: ListTile(
                                            contentPadding: EdgeInsets.zero,
                                            title: Text(
                                              subSec.title,
                                              style: _applyFont(theme.textTheme.titleSmall, fontFamily)
                                                  ?.copyWith(fontWeight: FontWeight.w700),
                                            ),
                                            subtitle: Text(
                                              subSec.repeatable ? 'Repeatable sub-section' : 'Single sub-section',
                                              style: _applyFont(theme.textTheme.bodySmall, fontFamily)
                                                  ?.copyWith(color: AppColors.textMuted),
                                            ),
                                            onTap: () {
                                              ref.read(formBuilderProvider.notifier).selectElement(subSec.id);
                                              widget.onSubSectionActivated(subSec.id);
                                            },
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: AppSpacing.sm),
                                      if (isActiveSub)
                                        const Chip(
                                          label: Text('Active'),
                                          visualDensity: VisualDensity.compact,
                                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                        )
                                      else
                                        OutlinedButton(
                                          onPressed: () => widget.onSubSectionActivated(subSec.id),
                                          child: const Text('Set active'),
                                        ),
                                    ],
                                  ),
                                  const SizedBox(height: AppSpacing.sm),

                                  // Drag and drop zone with drop targets
                                  _buildDropTarget(subSec.id, 0, canvasPrimary),
                                  if (subSec.questions.isEmpty)
                                    Container(
                                      width: double.infinity,
                                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.xl),
                                      decoration: AppSurfaceStyles.insetCard(tint: canvasBg.withValues(alpha: 0.5)),
                                      child: Text(
                                        'Empty sub-section. Drag fields here.',
                                        textAlign: TextAlign.center,
                                        style: _applyFont(theme.textTheme.bodySmall, fontFamily)?.copyWith(
                                          fontStyle: FontStyle.italic,
                                          color: AppColors.textMuted,
                                        ),
                                      ),
                                    )
                                  else
                                    Column(
                                      children: List.generate(subSec.questions.length, (qIdx) {
                                        final q = subSec.questions[qIdx];
                                        final isSelectedQ = builderState.selectedElementId == q.id;

                                        Widget questionTile = Container(
                                          decoration: AppSurfaceStyles.insetCard(
                                            selected: isSelectedQ,
                                            tint: isSelectedQ ? canvasPrimary.withValues(alpha: 0.15) : canvasBg,
                                            radiusValue: radius * 0.7,
                                          ),
                                          child: Material(
                                            color: Colors.transparent,
                                            child: Column(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                if (isSelectedQ) ...[
                                                  _InlinePopover(question: q),
                                                  const Divider(height: 1),
                                                ],
                                                ListTile(
                                                  leading: const Icon(Icons.drag_indicator, color: AppColors.textMuted),
                                                  title: Text(
                                                    q.label,
                                                    style: _applyFont(theme.textTheme.bodyMedium, fontFamily)
                                                        ?.copyWith(fontWeight: FontWeight.w600),
                                                  ),
                                                  subtitle: Text(
                                                    q.description.isNotEmpty ? q.description : 'Type: ${q.type}',
                                                    style: _applyFont(theme.textTheme.bodySmall, fontFamily)
                                                        ?.copyWith(color: AppColors.textMuted),
                                                  ),
                                                  trailing: q.required
                                                      ? const Chip(
                                                          label: Text('Required'),
                                                          labelStyle: TextStyle(fontSize: 11),
                                                          visualDensity: VisualDensity.compact,
                                                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                                        )
                                                      : null,
                                                  onTap: () {
                                                    ref.read(formBuilderProvider.notifier).selectElement(q.id);
                                                  },
                                                ),
                                              ],
                                            ),
                                          ),
                                        );

                                        return Column(
                                          children: [
                                            Draggable<Map<String, dynamic>>(
                                              data: {
                                                'source': 'canvas',
                                                'questionId': q.id,
                                                'fromSubSecId': subSec.id,
                                              },
                                              feedback: SizedBox(
                                                width: 300,
                                                child: Material(
                                                  elevation: 8,
                                                  borderRadius: BorderRadius.circular(radius * 0.7),
                                                  child: questionTile,
                                                ),
                                              ),
                                              childWhenDragging: Opacity(
                                                opacity: 0.3,
                                                child: questionTile,
                                              ),
                                              child: questionTile,
                                            ),
                                            _buildDropTarget(subSec.id, qIdx + 1, canvasPrimary),
                                          ],
                                        );
                                      }),
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
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildDropTarget(String subSecId, int index, Color canvasPrimary) {
    final targetId = 'target_${subSecId}_$index';
    return DragTarget<Map<String, dynamic>>(
      onWillAccept: (data) => true,
      onAcceptWithDetails: (details) {
        final data = details.data;
        final source = data['source'] as String;
        if (source == 'library') {
          final type = data['type'] as String;
          final qId = 'q_${DateTime.now().millisecondsSinceEpoch}';
          final newQ = FormQuestion(
            id: qId,
            type: type,
            label: 'New Question ($type)',
            properties: const {'placeholder': 'Enter value'},
          );
          ref.read(formBuilderProvider.notifier).insertQuestion(subSecId, index, newQ);
        } else if (source == 'canvas') {
          final qId = data['questionId'] as String;
          final fromSubSecId = data['fromSubSecId'] as String;
          ref.read(formBuilderProvider.notifier).moveQuestion(
                fromSubSecId: fromSubSecId,
                toSubSecId: subSecId,
                questionId: qId,
                toIndex: index,
              );
        }
        setState(() {
          _hoveredTargetId = null;
        });
      },
      onMove: (details) {
        if (_hoveredTargetId != targetId) {
          setState(() {
            _hoveredTargetId = targetId;
          });
        }
      },
      onLeave: (data) {
        if (_hoveredTargetId == targetId) {
          setState(() {
            _hoveredTargetId = null;
          });
        }
      },
      builder: (context, candidateData, rejectedData) {
        final isHovered = _hoveredTargetId == targetId;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          height: isHovered ? 36.0 : 6.0,
          margin: const EdgeInsets.symmetric(vertical: 2),
          decoration: BoxDecoration(
            color: isHovered ? canvasPrimary.withValues(alpha: 0.1) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
            border: isHovered
                ? Border.all(color: canvasPrimary, width: 1.5, style: BorderStyle.solid)
                : null,
          ),
          child: isHovered
              ? Center(
                  child: Text(
                    'Drop to place field here',
                    style: TextStyle(color: canvasPrimary, fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                )
              : const SizedBox.shrink(),
        );
      },
    );
  }

  Widget _buildPlay(FormBuilderState builderState, FormPlayState playState, Color canvasBg, Color canvasPrimary, String fontFamily, double radius) {
    final theme = Theme.of(context);
    final visibleSections = builderState.sections.where((sec) {
      return _evaluateVisibilityRule(sec.visibilityRule ?? '', playState.answers);
    }).toList();

    final hiddenSections = builderState.sections.where((sec) {
      return !_evaluateVisibilityRule(sec.visibilityRule ?? '', playState.answers);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Testing header
        Container(
          padding: const EdgeInsets.all(8),
          color: Colors.amber.withValues(alpha: 0.15),
          child: const Row(
            children: [
              Icon(Icons.science_outlined, color: Colors.amber, size: 16),
              SizedBox(width: 8),
              Text(
                'Interactive Play Mode - Testing Runtime (Isolated State)',
                style: TextStyle(color: Colors.amber, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Expanded(
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              if (hiddenSections.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Container(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.builderDivider),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Branch Logic Outcomes:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                        const SizedBox(height: 4),
                        ...hiddenSections.map((sec) => Text(
                              '• Section "${sec.title}" hidden (Rule: "${sec.visibilityRule}")',
                              style: TextStyle(color: theme.colorScheme.error, fontSize: 11),
                            )),
                      ],
                    ),
                  ),
                ),
              if (visibleSections.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32.0),
                    child: Text('No active sections configured or visible.', style: TextStyle(color: AppColors.textMuted)),
                  ),
                )
              else
                ...visibleSections.map((sec) {
                  return Container(
                    margin: const EdgeInsets.only(bottom: AppSpacing.md),
                    decoration: AppSurfaceStyles.card(
                      tint: canvasBg,
                      radiusValue: radius,
                    ),
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          sec.title,
                          style: _applyFont(theme.textTheme.titleMedium, fontFamily)?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        if (sec.description.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            sec.description,
                            style: _applyFont(theme.textTheme.bodySmall, fontFamily)?.copyWith(color: AppColors.textMuted),
                          ),
                        ],
                        const Divider(height: 24),
                        ...sec.subSections.map((subSec) {
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: subSec.questions.map((q) {
                              final hasError = playState.validationErrors.containsKey(q.id);
                              final error = playState.validationErrors[q.id];

                              return Padding(
                                padding: const EdgeInsets.only(bottom: AppSpacing.md),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${q.label}${q.required ? ' *' : ''}',
                                      style: _applyFont(theme.textTheme.bodyMedium, fontFamily)?.copyWith(fontWeight: FontWeight.w600),
                                    ),
                                    if (q.description.isNotEmpty) ...[
                                      const SizedBox(height: 2),
                                      Text(
                                        q.description,
                                        style: _applyFont(theme.textTheme.bodySmall, fontFamily)?.copyWith(color: AppColors.textMuted),
                                      ),
                                    ],
                                    const SizedBox(height: AppSpacing.sm),
                                    _buildInteractiveField(q, playState),
                                    if (hasError) ...[
                                      const SizedBox(height: 4),
                                      Text(
                                        error!,
                                        style: TextStyle(color: theme.colorScheme.error, fontSize: 12),
                                      ),
                                    ],
                                  ],
                                ),
                              );
                            }).toList(),
                          );
                        }),
                      ],
                    ),
                  );
                }),
              const SizedBox(height: AppSpacing.md),
              FilledButton(
                onPressed: () {
                  // Validate all visible questions
                  bool isValid = true;
                  for (final sec in visibleSections) {
                    for (final subSec in sec.subSections) {
                      for (final q in subSec.questions) {
                        final val = playState.answers[q.id];
                        if (q.required && (val == null || val.toString().trim().isEmpty)) {
                          ref.read(formPlayProvider.notifier).setError(q.id, 'This field is required');
                          isValid = false;
                        } else {
                          ref.read(formPlayProvider.notifier).clearError(q.id);
                        }
                      }
                    }
                  }
                  if (isValid) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        backgroundColor: theme.colorScheme.primaryContainer,
                        content: Text(
                          'Test response submitted successfully! Answers: ${playState.answers}',
                          style: TextStyle(color: theme.colorScheme.onPrimaryContainer),
                        ),
                      ),
                    );
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        backgroundColor: Colors.red,
                        content: Text('Please correct validation errors before submitting.'),
                      ),
                    );
                  }
                },
                style: FilledButton.styleFrom(
                  backgroundColor: canvasPrimary,
                  foregroundColor: canvasBg.computeLuminance() > 0.5 ? Colors.white : Colors.black,
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text('Submit Test Response'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildInteractiveField(FormQuestion q, FormPlayState playState) {
    final value = playState.answers[q.id];

    switch (q.type) {
      case 'text_input':
        return TextField(
          key: ValueKey('input_${q.id}'),
          decoration: const InputDecoration(border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formPlayProvider.notifier).setAnswer(q.id, val);
            if (q.required && val.trim().isEmpty) {
              ref.read(formPlayProvider.notifier).setError(q.id, 'This field is required');
            } else {
              ref.read(formPlayProvider.notifier).clearError(q.id);
            }
          },
        );
      case 'dropdown':
        final options = q.properties['options'] as List?;
        final items = options != null
            ? options.map((opt) {
                final label = opt['label']?.toString() ?? opt['value']?.toString() ?? '';
                final val = opt['value']?.toString() ?? '';
                return DropdownMenuItem<String>(value: val, child: Text(label));
              }).toList()
            : [const DropdownMenuItem<String>(value: 'yes', child: Text('Yes')), const DropdownMenuItem<String>(value: 'no', child: Text('No'))];

        return DropdownButtonFormField<String>(
          key: ValueKey('input_${q.id}'),
          value: value?.toString(),
          decoration: const InputDecoration(border: OutlineInputBorder()),
          items: items,
          onChanged: (val) {
            ref.read(formPlayProvider.notifier).setAnswer(q.id, val);
            ref.read(formPlayProvider.notifier).clearError(q.id);
          },
        );
      case 'checkbox':
        return CheckboxListTile(
          key: ValueKey('input_${q.id}'),
          contentPadding: EdgeInsets.zero,
          title: Text(q.properties['placeholder']?.toString() ?? 'Accept option'),
          value: value == true,
          onChanged: (val) {
            ref.read(formPlayProvider.notifier).setAnswer(q.id, val);
            ref.read(formPlayProvider.notifier).clearError(q.id);
          },
        );
      case 'toggle':
        return SwitchListTile(
          key: ValueKey('input_${q.id}'),
          contentPadding: EdgeInsets.zero,
          title: Text(q.properties['placeholder']?.toString() ?? 'Enable feature'),
          value: value == true,
          onChanged: (val) {
            ref.read(formPlayProvider.notifier).setAnswer(q.id, val);
            ref.read(formPlayProvider.notifier).clearError(q.id);
          },
        );
      case 'rating':
        final double currentRating = double.tryParse(value?.toString() ?? '0') ?? 0;
        return Row(
          key: ValueKey('input_${q.id}'),
          children: List.generate(5, (starIdx) {
            return IconButton(
              icon: Icon(
                starIdx < currentRating ? Icons.star : Icons.star_border,
                color: Colors.amber,
              ),
              onPressed: () {
                ref.read(formPlayProvider.notifier).setAnswer(q.id, starIdx + 1);
                ref.read(formPlayProvider.notifier).clearError(q.id);
              },
            );
          }),
        );
      default:
        return Text('Unsupported interactive type: ${q.type}');
    }
  }
}

class _InlinePopover extends ConsumerStatefulWidget {
  final FormQuestion question;
  const _InlinePopover({required this.question});

  @override
  ConsumerState<_InlinePopover> createState() => _InlinePopoverState();
}

class _InlinePopoverState extends ConsumerState<_InlinePopover> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.question.label);
  }

  @override
  void didUpdateWidget(covariant _InlinePopover oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.question.label != _controller.text) {
      _controller.text = widget.question.label;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final builderState = ref.read(formBuilderProvider);
    final canvasPrimary = _parseHexColor(builderState.style.primaryColor, theme.primaryColor);

    return Focus(
      onKeyEvent: (node, event) {
        if (event.logicalKey == LogicalKeyboardKey.escape) {
          ref.read(formBuilderProvider.notifier).selectElement(null);
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Expanded(
              child: SizedBox(
                height: 36,
                child: TextField(
                  key: const ValueKey('popover-label-input'),
                  controller: _controller,
                  style: const TextStyle(fontSize: 13),
                  decoration: const InputDecoration(
                    hintText: 'Field Label',
                    isDense: true,
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  ),
                  onChanged: (val) {
                    ref.read(formBuilderProvider.notifier).updateQuestion(widget.question.id, label: val);
                  },
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            const Text('Required:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
            const SizedBox(width: 4),
            SizedBox(
              width: 40,
              height: 24,
              child: FittedBox(
                fit: BoxFit.fill,
                child: Switch(
                  key: const ValueKey('popover-required-switch'),
                  value: widget.question.required,
                  onChanged: (val) {
                    ref.read(formBuilderProvider.notifier).updateQuestion(widget.question.id, required: val);
                  },
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            IconButton(
              key: const ValueKey('popover-close-button'),
              icon: const Icon(Icons.close, size: 20),
              onPressed: () {
                ref.read(formBuilderProvider.notifier).selectElement(null);
              },
            ),
          ],
        ),
      ),
    );
  }
}

