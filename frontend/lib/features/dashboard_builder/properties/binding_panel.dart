import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/tokens.dart';
import '../models/widget_model.dart';
import '../providers/canvas_state_provider.dart';

class BindingPanel extends ConsumerWidget {
  final String dashboardId;
  final WidgetModel widget;

  const BindingPanel({
    super.key,
    required this.dashboardId,
    required this.widget,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final binding = widget.dataBinding;
    final currentMode = binding?.refreshMode ?? 'with_dashboard';

    // Mock analyses in the project for mapping
    final List<Map<String, String>> mockAnalyses = [
      {'id': 'analysis_1', 'name': 'Response Trends Analysis'},
      {'id': 'analysis_2', 'name': 'Outcomes Demographic Summary'},
    ];

    // Mock output nodes for selected analysis
    final List<Map<String, String>> mockNodes = [
      {
        'id': 'node_1',
        'name': 'Total Count Indicator (KPI)',
        'type': 'kpi_value',
      },
      {
        'id': 'node_2',
        'name': 'Categorical Chart Data (Chart)',
        'type': 'chart_data',
      },
      {'id': 'node_3', 'name': 'Tabular List Report (Table)', 'type': 'table'},
    ];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Data binding',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
            ),
          ),
          const Divider(),
          const SizedBox(height: AppSpacing.sm),

          // Analysis Selection
          Text(
            'Analysis source',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          DropdownButtonFormField<String>(
            value: binding?.analysisId,
            hint: const Text('Select Analysis'),
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: mockAnalyses.map((item) {
              return DropdownMenuItem<String>(
                value: item['id'],
                child: Text(item['name']!),
              );
            }).toList(),
            onChanged: (val) {
              final newBinding = DataBinding(
                analysisId: val,
                nodeId: binding?.nodeId,
                refreshMode: currentMode,
                refreshIntervalSeconds: binding?.refreshIntervalSeconds,
              );
              ref
                  .read(canvasStateProvider(dashboardId).notifier)
                  .updateWidgetBinding(widget.id, newBinding);
            },
          ),
          const SizedBox(height: AppSpacing.lg),

          // Output Node Selection
          Text(
            'Output node',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          DropdownButtonFormField<String>(
            value: binding?.nodeId,
            hint: const Text('Select Output Node'),
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: mockNodes.map((item) {
              return DropdownMenuItem<String>(
                value: item['id'],
                child: Text(item['name']!),
              );
            }).toList(),
            onChanged: (val) {
              final newBinding = DataBinding(
                analysisId: binding?.analysisId,
                nodeId: val,
                refreshMode: currentMode,
                refreshIntervalSeconds: binding?.refreshIntervalSeconds,
              );
              ref
                  .read(canvasStateProvider(dashboardId).notifier)
                  .updateWidgetBinding(widget.id, newBinding);
            },
          ),
          const SizedBox(height: AppSpacing.lg),

          // Refresh Mode Selection
          Text(
            'Refresh mode',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          RadioListTile<String>(
            title: Text(
              'With dashboard',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            value: 'with_dashboard',
            groupValue: currentMode,
            dense: true,
            onChanged: (val) => _updateMode(ref, val!),
          ),
          RadioListTile<String>(
            title: Text(
              'Independent',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            value: 'independent',
            groupValue: currentMode,
            dense: true,
            onChanged: (val) => _updateMode(ref, val!),
          ),
          if (currentMode == 'independent') ...[
            Padding(
              padding: const EdgeInsets.only(
                left: AppSpacing.xxxl,
                right: AppSpacing.lg,
              ),
              child: TextFormField(
                initialValue: (binding?.refreshIntervalSeconds ?? 30)
                    .toString(),
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Interval (seconds)',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                onChanged: (val) {
                  final parsed = int.tryParse(val) ?? 30;
                  final newBinding = DataBinding(
                    analysisId: binding?.analysisId,
                    nodeId: binding?.nodeId,
                    refreshMode: 'independent',
                    refreshIntervalSeconds: parsed,
                  );
                  ref
                      .read(canvasStateProvider(dashboardId).notifier)
                      .updateWidgetBinding(widget.id, newBinding);
                },
              ),
            ),
          ],
          RadioListTile<String>(
            title: Text('Never', style: Theme.of(context).textTheme.bodySmall),
            value: 'never',
            groupValue: currentMode,
            dense: true,
            onChanged: (val) => _updateMode(ref, val!),
          ),
        ],
      ),
    );
  }

  void _updateMode(WidgetRef ref, String mode) {
    final binding = widget.dataBinding;
    final newBinding = DataBinding(
      analysisId: binding?.analysisId,
      nodeId: binding?.nodeId,
      refreshMode: mode,
      refreshIntervalSeconds: binding?.refreshIntervalSeconds ?? 30,
    );
    ref
        .read(canvasStateProvider(dashboardId).notifier)
        .updateWidgetBinding(widget.id, newBinding);
  }
}
