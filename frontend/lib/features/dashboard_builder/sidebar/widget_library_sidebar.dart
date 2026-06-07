import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/canvas_state_provider.dart';

class WidgetLibrarySidebar extends ConsumerWidget {
  final String dashboardId;

  const WidgetLibrarySidebar({
    super.key,
    required this.dashboardId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<Map<String, dynamic>> widgetsList = [
      {
        'category': 'Charts',
        'items': [
          {'type': 'bar_chart', 'label': 'Bar Chart', 'icon': Icons.bar_chart},
          {'type': 'line_chart', 'label': 'Line Chart', 'icon': Icons.show_chart},
          {'type': 'pie_chart', 'label': 'Pie Chart', 'icon': Icons.pie_chart},
        ]
      },
      {
        'category': 'Data Display',
        'items': [
          {'type': 'kpi_card', 'label': 'KPI Metric Card', 'icon': Icons.dashboard_customize},
          {'type': 'data_table', 'label': 'Data Table Report', 'icon': Icons.table_chart},
        ]
      },
      {
        'category': 'Content Layout',
        'items': [
          {'type': 'text_label', 'label': 'Text Label', 'icon': Icons.title},
          {'type': 'image_widget', 'label': 'Image Box', 'icon': Icons.image},
          {'type': 'divider_widget', 'label': 'Spacer Divider', 'icon': Icons.remove},
        ]
      },
      {
        'category': 'Interactive Controls',
        'items': [
          {'type': 'filter_widget', 'label': 'Dropdown/Search Filter', 'icon': Icons.filter_alt},
        ]
      }
    ];

    return Drawer(
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            color: Theme.of(context).primaryColor,
            child: const Row(
              children: [
                Icon(Icons.widgets, color: Colors.white),
                SizedBox(width: 8),
                Text(
                  'WIDGET PALETTE',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: widgetsList.length,
              itemBuilder: (context, catIdx) {
                final category = widgetsList[catIdx];
                return ExpansionTile(
                  initiallyExpanded: true,
                  title: Text(
                    category['category'],
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                  children: (category['items'] as List).map((item) {
                    return ListTile(
                      dense: true,
                      leading: Icon(item['icon'], size: 20),
                      title: Text(item['label']),
                      trailing: const Icon(Icons.add, size: 16),
                      onTap: () {
                        // Click to add at center of viewport
                        ref.read(canvasStateProvider(dashboardId).notifier).addWidget(
                              type: item['type'],
                              position: const Offset(400, 200),
                            );
                      },
                    );
                  }).toList(),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
