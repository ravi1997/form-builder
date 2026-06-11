import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../providers/form_builder_provider.dart';

class ElementsPanel extends ConsumerWidget {
  final String activeSubSectionId;

  const ElementsPanel({super.key, required this.activeSubSectionId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final elementTypes = [
      {'type': 'text_input', 'label': 'Text field', 'icon': Icons.text_fields},
      {
        'type': 'dropdown',
        'label': 'Dropdown selector',
        'icon': Icons.arrow_drop_down_circle,
      },
      {
        'type': 'date_range_picker',
        'label': 'Date range picker',
        'icon': Icons.date_range,
      },
      {
        'type': 'multi_select',
        'label': 'Multi-select options',
        'icon': Icons.playlist_add_check,
      },
      {'type': 'rating', 'label': 'Star rating', 'icon': Icons.star},
      {
        'type': 'checkbox',
        'label': 'Checkbox list tile',
        'icon': Icons.check_box,
      },
      {'type': 'toggle', 'label': 'Switch toggle', 'icon': Icons.toggle_on},
    ];

    return Container(
      decoration: AppSurfaceStyles.card(),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: AppSurfaceStyles.insetCard(
                    tint: AppColors.brandPrimarySoft,
                  ),
                  child: const Icon(
                    Icons.widgets_outlined,
                    color: AppColors.brandPrimary,
                    size: 18,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Field library',
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      Text(
                        'Insert controls into $activeSubSectionId',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'Choose a component to add it to the selected sub-section.',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.md),
            Expanded(
              child: ListView.separated(
                padding: EdgeInsets.zero,
                itemCount: elementTypes.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: AppSpacing.xs),
                itemBuilder: (context, index) {
                  final el = elementTypes[index];
                  return Material(
                    color: AppColors.surfaceCardAlt,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      onTap: () {
                        ref
                            .read(formBuilderProvider.notifier)
                            .addQuestion(
                              activeSubSectionId,
                              el['type'] as String,
                            );
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.md,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              el['icon'] as IconData,
                              color: AppColors.brandPrimary,
                              size: 20,
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: Text(
                                el['label'] as String,
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(fontWeight: FontWeight.w600),
                              ),
                            ),
                            const Icon(
                              Icons.add,
                              size: 18,
                              color: AppColors.textMuted,
                            ),
                          ],
                        ),
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
