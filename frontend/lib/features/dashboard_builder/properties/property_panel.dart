import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/widget_model.dart';
import '../providers/canvas_state_provider.dart';
import 'binding_panel.dart';

class PropertyPanel extends ConsumerStatefulWidget {
  final String dashboardId;

  const PropertyPanel({
    super.key,
    required this.dashboardId,
  });

  @override
  ConsumerState<PropertyPanel> createState() => _PropertyPanelState();
}

class _PropertyPanelState extends ConsumerState<PropertyPanel> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(canvasStateProvider(widget.dashboardId));
    final selectedId = state.selectedWidgetId;

    if (selectedId == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(16.0),
          child: Text(
            'Select a widget to edit its properties or drag one from the library sidebar.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
        ),
      );
    }

    final widgetModel = state.widgets.firstWhere(
      (w) => w.id == selectedId,
      orElse: () => const WidgetModel(
        id: '',
        type: 'none',
        position: WidgetPosition(x: 0, y: 0),
        size: WidgetSize(width: 0, height: 0),
        properties: {},
      ),
    );

    if (widgetModel.id.isEmpty) {
      return const SizedBox.shrink();
    }

    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(48),
        child: AppBar(
          bottom: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: 'General'),
              Tab(text: 'Data'),
              Tab(text: 'Style'),
            ],
          ),
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildGeneralTab(widgetModel),
          BindingPanel(dashboardId: widget.dashboardId, widget: widgetModel),
          _buildStyleTab(widgetModel),
        ],
      ),
    );
  }

  Widget _buildGeneralTab(WidgetModel w) {
    final props = w.properties;
    final notifier = ref.read(canvasStateProvider(widget.dashboardId).notifier);

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        TextFormField(
          initialValue: props['title'] ?? '',
          decoration: const InputDecoration(labelText: 'Widget Title', border: OutlineInputBorder()),
          onChanged: (val) {
            notifier.updateWidgetProperties(w.id, {'title': val});
          },
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          title: const Text('Show Title Header'),
          value: props['show_title'] ?? true,
          onChanged: (val) {
            notifier.updateWidgetProperties(w.id, {'show_title': val});
          },
        ),
        SwitchListTile(
          title: const Text('Lock Widget Position'),
          value: w.isLocked,
          onChanged: (val) {
            notifier.toggleLockWidget(w.id);
          },
        ),
        const SizedBox(height: 12),
        const Text('Geometry Bounds', style: TextStyle(fontWeight: FontWeight.bold)),
        const Divider(),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                key: ValueKey('x-${w.position.x}'),
                initialValue: w.position.x.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'X'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.position.x;
                  notifier.moveWidget(w.id, parsed, w.position.y);
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                key: ValueKey('y-${w.position.y}'),
                initialValue: w.position.y.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Y'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.position.y;
                  notifier.moveWidget(w.id, w.position.x, parsed);
                },
              ),
            ),
          ],
        ),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                key: ValueKey('w-${w.size.width}'),
                initialValue: w.size.width.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Width'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.size.width;
                  notifier.resizeWidget(w.id, w.position.x, w.position.y, parsed, w.size.height);
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                key: ValueKey('h-${w.size.height}'),
                initialValue: w.size.height.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Height'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.size.height;
                  notifier.resizeWidget(w.id, w.position.x, w.position.y, w.size.width, parsed);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        const Text('Layers (Z-Index)', style: TextStyle(fontWeight: FontWeight.bold)),
        const Divider(),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            ElevatedButton(
              onPressed: () => notifier.bringToFront(w.id),
              child: const Text('Bring Front'),
            ),
            ElevatedButton(
              onPressed: () => notifier.sendToBack(w.id),
              child: const Text('Send Back'),
            ),
          ],
        ),
        const SizedBox(height: 24),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
          ),
          onPressed: () {
            notifier.deleteWidget(w.id);
          },
          icon: const Icon(Icons.delete),
          label: const Text('Delete Widget'),
        ),
      ],
    );
  }

  Widget _buildStyleTab(WidgetModel w) {
    final props = w.properties;
    final notifier = ref.read(canvasStateProvider(widget.dashboardId).notifier);

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        const Text('Visual Decorator', style: TextStyle(fontWeight: FontWeight.bold)),
        const Divider(),
        TextFormField(
          initialValue: props['background_color'] ?? '#FFFFFF',
          decoration: const InputDecoration(labelText: 'Background Color (HEX)'),
          onFieldSubmitted: (val) {
            notifier.updateWidgetProperties(w.id, {'background_color': val});
          },
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: props['border_color'] ?? '#E0E0E0',
          decoration: const InputDecoration(labelText: 'Border Color (HEX)'),
          onFieldSubmitted: (val) {
            notifier.updateWidgetProperties(w.id, {'border_color': val});
          },
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: (props['border_radius'] ?? 8.0).toString(),
          decoration: const InputDecoration(labelText: 'Border Radius (px)'),
          keyboardType: TextInputType.number,
          onFieldSubmitted: (val) {
            final parsed = double.tryParse(val) ?? 8.0;
            notifier.updateWidgetProperties(w.id, {'border_radius': parsed});
          },
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: (props['padding'] ?? 16.0).toString(),
          decoration: const InputDecoration(labelText: 'Padding (px)'),
          keyboardType: TextInputType.number,
          onFieldSubmitted: (val) {
            final parsed = double.tryParse(val) ?? 16.0;
            notifier.updateWidgetProperties(w.id, {'padding': parsed});
          },
        ),

        // Widget-specific style properties
        if (w.type == 'kpi_card') ...[
          const SizedBox(height: 16),
          const Text('KPI Specific Styles', style: TextStyle(fontWeight: FontWeight.bold)),
          const Divider(),
          DropdownButtonFormField<String>(
            value: props['value_format'] ?? 'number',
            decoration: const InputDecoration(labelText: 'Value Format'),
            items: const [
              DropdownMenuItem(value: 'number', child: Text('Number')),
              DropdownMenuItem(value: 'currency', child: Text('Currency')),
              DropdownMenuItem(value: 'percentage', child: Text('Percentage')),
              DropdownMenuItem(value: 'compact', child: Text('Compact')),
            ],
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'value_format': val});
            },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: props['prefix'] ?? '',
            decoration: const InputDecoration(labelText: 'Prefix'),
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'prefix': val});
            },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: props['suffix'] ?? '',
            decoration: const InputDecoration(labelText: 'Suffix'),
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'suffix': val});
            },
          ),
        ],

        if (w.type == 'filter_widget') ...[
          const SizedBox(height: 16),
          const Text('Filter Configuration', style: TextStyle(fontWeight: FontWeight.bold)),
          const Divider(),
          DropdownButtonFormField<String>(
            value: props['filter_type'] ?? 'dropdown',
            decoration: const InputDecoration(labelText: 'Filter Input UI Type'),
            items: const [
              DropdownMenuItem(value: 'dropdown', child: Text('Dropdown Option Selector')),
              DropdownMenuItem(value: 'text_search', child: Text('Text Search Input')),
              DropdownMenuItem(value: 'date_range_picker', child: Text('Date Range Picker')),
            ],
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'filter_type': val});
            },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: (props['static_options'] as List?)?.join(', ') ?? '',
            decoration: const InputDecoration(labelText: 'Static Options (comma separated)'),
            onFieldSubmitted: (val) {
              final options = val.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
              notifier.updateWidgetProperties(w.id, {'static_options': options});
            },
          ),
        ]
      ],
    );
  }
}
