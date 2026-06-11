import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../providers/form_builder_provider.dart';

class BuilderCanvas extends ConsumerWidget {
  final String? activeSubSectionId;
  final void Function(String) onSubSectionActivated;

  const BuilderCanvas({
    super.key,
    required this.activeSubSectionId,
    required this.onSubSectionActivated,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final builderState = ref.watch(formBuilderProvider);
    final theme = Theme.of(context);

    return Container(
      decoration: AppSurfaceStyles.card(),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Canvas',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        'Compose sections, sub-sections, and questions in a single workspace.',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                FilledButton.icon(
                  onPressed: () {
                    ref.read(formBuilderProvider.notifier).addSection();
                  },
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Add section'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Expanded(
              child: ListView.separated(
                padding: EdgeInsets.zero,
                itemCount: builderState.sections.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: AppSpacing.md),
                itemBuilder: (context, sIndex) {
                  final section = builderState.sections[sIndex];
                  final isSelectedSec =
                      builderState.selectedElementId == section.id;

                  return Container(
                    decoration: AppSurfaceStyles.card(
                      selected: isSelectedSec,
                      tint: isSelectedSec
                          ? AppColors.brandPrimarySoft
                          : AppColors.surfaceCard,
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
                                child: ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  title: Text(
                                    section.title,
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(fontWeight: FontWeight.w800),
                                  ),
                                  subtitle: Text(
                                    section.description.isNotEmpty
                                        ? section.description
                                        : 'No description',
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color: AppColors.textMuted,
                                    ),
                                  ),
                                  onTap: () {
                                    ref
                                        .read(formBuilderProvider.notifier)
                                        .selectElement(section.id);
                                  },
                                ),
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              FilledButton.tonalIcon(
                                onPressed: () {
                                  ref
                                      .read(formBuilderProvider.notifier)
                                      .addSubSection(section.id);
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
                            final isSelectedSub =
                                builderState.selectedElementId == subSec.id;
                            final isActiveSub = activeSubSectionId == subSec.id;

                            return Padding(
                              padding: const EdgeInsets.only(
                                bottom: AppSpacing.sm,
                              ),
                              child: Container(
                                decoration: AppSurfaceStyles.insetCard(
                                  selected: isSelectedSub || isActiveSub,
                                  tint: isActiveSub
                                      ? AppColors.brandPrimarySoft
                                      : AppColors.surfaceCardAlt,
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.all(AppSpacing.md),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: ListTile(
                                              contentPadding: EdgeInsets.zero,
                                              title: Text(
                                                subSec.title,
                                                style: theme
                                                    .textTheme
                                                    .titleSmall
                                                    ?.copyWith(
                                                      fontWeight:
                                                          FontWeight.w700,
                                                    ),
                                              ),
                                              subtitle: Text(
                                                subSec.repeatable
                                                    ? 'Repeatable sub-section'
                                                    : 'Single sub-section',
                                                style: theme.textTheme.bodySmall
                                                    ?.copyWith(
                                                      color:
                                                          AppColors.textMuted,
                                                    ),
                                              ),
                                              onTap: () {
                                                ref
                                                    .read(
                                                      formBuilderProvider
                                                          .notifier,
                                                    )
                                                    .selectElement(subSec.id);
                                                onSubSectionActivated(
                                                  subSec.id,
                                                );
                                              },
                                            ),
                                          ),
                                          const SizedBox(width: AppSpacing.sm),
                                          if (isActiveSub)
                                            const Chip(
                                              label: Text('Active'),
                                              visualDensity:
                                                  VisualDensity.compact,
                                              materialTapTargetSize:
                                                  MaterialTapTargetSize
                                                      .shrinkWrap,
                                            )
                                          else
                                            OutlinedButton(
                                              onPressed: () =>
                                                  onSubSectionActivated(
                                                    subSec.id,
                                                  ),
                                              child: const Text('Set active'),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: AppSpacing.sm),
                                      if (subSec.questions.isEmpty)
                                        Container(
                                          width: double.infinity,
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: AppSpacing.lg,
                                            vertical: AppSpacing.xl,
                                          ),
                                          decoration:
                                              AppSurfaceStyles.insetCard(
                                                tint: AppColors.surfaceCard,
                                              ),
                                          child: Text(
                                            'Empty sub-section. Add fields from the library.',
                                            textAlign: TextAlign.center,
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                                  fontStyle: FontStyle.italic,
                                                  color: AppColors.textMuted,
                                                ),
                                          ),
                                        )
                                      else
                                        Column(
                                          children: subSec.questions.map((q) {
                                            final isSelectedQ =
                                                builderState
                                                    .selectedElementId ==
                                                q.id;

                                            return Padding(
                                              padding: const EdgeInsets.only(
                                                bottom: AppSpacing.xs,
                                              ),
                                              child: Container(
                                                decoration:
                                                    AppSurfaceStyles.insetCard(
                                                      selected: isSelectedQ,
                                                      tint: isSelectedQ
                                                          ? AppColors
                                                                .brandPrimarySoft
                                                          : AppColors
                                                                .surfaceCard,
                                                    ),
                                                child: ListTile(
                                                  leading: const Icon(
                                                    Icons.drag_indicator,
                                                    color: AppColors.textMuted,
                                                  ),
                                                  title: Text(
                                                    q.label,
                                                    style: theme
                                                        .textTheme
                                                        .bodyMedium
                                                        ?.copyWith(
                                                          fontWeight:
                                                              FontWeight.w600,
                                                        ),
                                                  ),
                                                  subtitle: Text(
                                                    q.description.isNotEmpty
                                                        ? q.description
                                                        : 'Type: ${q.type}',
                                                    style: theme
                                                        .textTheme
                                                        .bodySmall
                                                        ?.copyWith(
                                                          color: AppColors
                                                              .textMuted,
                                                        ),
                                                  ),
                                                  trailing: q.required
                                                      ? const Chip(
                                                          label: Text(
                                                            'Required',
                                                          ),
                                                          labelStyle: TextStyle(
                                                            fontSize: 11,
                                                          ),
                                                          visualDensity:
                                                              VisualDensity
                                                                  .compact,
                                                          materialTapTargetSize:
                                                              MaterialTapTargetSize
                                                                  .shrinkWrap,
                                                        )
                                                      : null,
                                                  onTap: () {
                                                    ref
                                                        .read(
                                                          formBuilderProvider
                                                              .notifier,
                                                        )
                                                        .selectElement(q.id);
                                                  },
                                                ),
                                              ),
                                            );
                                          }).toList(),
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
        ),
      ),
    );
  }
}
