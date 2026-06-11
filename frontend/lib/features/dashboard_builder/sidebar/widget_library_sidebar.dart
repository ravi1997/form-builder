import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/design_system.dart';
import '../../../core/theme/tokens.dart';
import '../providers/canvas_state_provider.dart';

class WidgetLibrarySidebar extends ConsumerWidget {
  final String dashboardId;

  const WidgetLibrarySidebar({super.key, required this.dashboardId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<Map<String, dynamic>> widgetsList = [
      {
        'category': 'Charts',
        'items': [
          {'type': 'bar_chart', 'label': 'Bar chart', 'icon': Icons.bar_chart},
          {
            'type': 'line_chart',
            'label': 'Line chart',
            'icon': Icons.show_chart,
          },
          {'type': 'pie_chart', 'label': 'Pie chart', 'icon': Icons.pie_chart},
        ],
      },
      {
        'category': 'Data display',
        'items': [
          {
            'type': 'kpi_card',
            'label': 'KPI metric card',
            'icon': Icons.dashboard_customize,
          },
          {
            'type': 'data_table',
            'label': 'Data table report',
            'icon': Icons.table_chart,
          },
        ],
      },
      {
        'category': 'Content layout',
        'items': [
          {'type': 'text_label', 'label': 'Text label', 'icon': Icons.title},
          {'type': 'image_widget', 'label': 'Image box', 'icon': Icons.image},
          {
            'type': 'divider_widget',
            'label': 'Spacer divider',
            'icon': Icons.remove,
          },
        ],
      },
      {
        'category': 'Interactive controls',
        'items': [
          {
            'type': 'filter_widget',
            'label': 'Dropdown/search filter',
            'icon': Icons.filter_alt,
          },
        ],
      },
    ];

    return Container(
      decoration: AppSurfaceStyles.card(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.lg),
            decoration: const BoxDecoration(
              color: AppColors.brandPrimary,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(AppRadius.lg),
                topRight: Radius.circular(AppRadius.lg),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.widgets_outlined,
                  color: AppColors.surfaceCard,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  'Widget library',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.surfaceCard,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.lg),
              itemCount: widgetsList.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(height: AppSpacing.md),
              itemBuilder: (context, catIdx) {
                final category = widgetsList[catIdx];
                return Container(
                  decoration: AppSurfaceStyles.insetCard(),
                  child: ExpansionTile(
                    tilePadding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg,
                    ),
                    childrenPadding: const EdgeInsets.only(
                      bottom: AppSpacing.sm,
                    ),
                    initiallyExpanded: true,
                    title: Text(
                      category['category'],
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    children: (category['items'] as List).map((item) {
                      return ListTile(
                        dense: true,
                        leading: Icon(
                          item['icon'],
                          size: 20,
                          color: AppColors.brandPrimary,
                        ),
                        title: Text(item['label']),
                        trailing: const Icon(Icons.add, size: 16),
                        onTap: () {
                          ref
                              .read(canvasStateProvider(dashboardId).notifier)
                              .addWidget(
                                type: item['type'],
                                position: const Offset(400, 200),
                              );
                        },
                      );
                    }).toList(),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
