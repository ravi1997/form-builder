import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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
      {'id': 'node_1', 'name': 'Total Count Indicator (KPI)', 'type': 'kpi_value'},
      {'id': 'node_2', 'name': 'Categorical Chart Data (Chart)', 'type': 'chart_data'},
      {'id': 'node_3', 'name': 'Tabular List Report (Table)', 'type': 'table'},
    ];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'DATA BINDING',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 1.1),
          ),
          const Divider(),
          const SizedBox(height: 8),

          // Analysis Selection
          const Text('Analysis Source', style: TextStyle(fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          DropdownButtonFormField<String>(
            value: binding?.analysisId,
            hint: const Text('Select Analysis'),
            decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
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
              ref.read(canvasStateProvider(dashboardId).notifier).updateWidgetBinding(widget.id, newBinding);
            },
          ),
          const SizedBox(height: 16),

          // Output Node Selection
          const Text('Output Node', style: TextStyle(fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          DropdownButtonFormField<String>(
            value: binding?.nodeId,
            hint: const Text('Select Output Node'),
            decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
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
              ref.read(canvasStateProvider(dashboardId).notifier).updateWidgetBinding(widget.id, newBinding);
            },
          ),
          const SizedBox(height: 16),

          // Refresh Mode Selection
          const Text('Refresh Mode', style: TextStyle(fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          RadioListTile<String>(
            title: const Text('With Dashboard', style: TextStyle(fontSize: 13)),
            value: 'with_dashboard',
            groupValue: currentMode,
            dense: true,
            onChanged: (val) => _updateMode(ref, val!),
          ),
          RadioListTile<String>(
            title: const Text('Independent', style: TextStyle(fontSize: 13)),
            value: 'independent',
            groupValue: currentMode,
            dense: true,
            onChanged: (val) => _updateMode(ref, val!),
          ),
          if (currentMode == 'independent') ...[
            Padding(
              padding: const EdgeInsets.only(left: 32.0, right: 16.0),
              child: TextFormField(
                initialValue: (binding?.refreshIntervalSeconds ?? 30).toString(),
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
                  ref.read(canvasStateProvider(dashboardId).notifier).updateWidgetBinding(widget.id, newBinding);
                },
              ),
            ),
          ],
          RadioListTile<String>(
            title: const Text('Never', style: TextStyle(fontSize: 13)),
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
    ref.read(canvasStateProvider(dashboardId).notifier).updateWidgetBinding(widget.id, newBinding);
  }
}
