import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/design_system.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/responsive.dart';
import 'canvas/dashboard_canvas.dart';
import 'models/dashboard_model.dart';
import 'presentation/widgets/dashboard_sharing_dialog.dart';
import 'properties/property_panel.dart';
import 'providers/canvas_state_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/widget_data_provider.dart';
import 'sidebar/widget_library_sidebar.dart';

class DashboardBuilderPage extends ConsumerStatefulWidget {
  final String dashboardId;

  const DashboardBuilderPage({super.key, required this.dashboardId});

  @override
  ConsumerState<DashboardBuilderPage> createState() =>
      _DashboardBuilderPageState();
}

class _DashboardBuilderPageState extends ConsumerState<DashboardBuilderPage> {
  DashboardModel? _dashboard;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    final service = ref.read(dashboardServiceProvider);
    final token = ref.read(authTokenProvider);

    try {
      final dbModel = await service.getDashboard(widget.dashboardId, token);
      setState(() {
        _dashboard = dbModel;
        _isLoading = false;
      });

      ref
          .read(canvasStateProvider(widget.dashboardId).notifier)
          .loadDashboard(dbModel);
      ref.read(widgetDataProvider(widget.dashboardId).notifier).refreshData();
      _setupAutoRefreshTimer(dbModel);
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _setupAutoRefreshTimer(DashboardModel dbModel) {
    ref
        .read(widgetDataProvider(widget.dashboardId).notifier)
        .setupAutoRefresh(
          enabled: dbModel.settings.autoRefresh,
          intervalSeconds: dbModel.settings.refreshIntervalSeconds,
        );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_dashboard == null) {
      return const Scaffold(
        body: Center(child: Text('Failed to load dashboard.')),
      );
    }

    final canvasState = ref.watch(canvasStateProvider(widget.dashboardId));
    final isEditMode = canvasState.mode == CanvasMode.edit;

    return Scaffold(
      backgroundColor: AppColors.builderBackground,
      appBar: AppBar(
        title: Text(
          canvasState.isDirty ? '${_dashboard!.name}*' : _dashboard!.name,
        ),
        actions: [
          if (isEditMode) ...[
            IconButton(
              icon: const Icon(Icons.undo),
              onPressed: () => ref
                  .read(canvasStateProvider(widget.dashboardId).notifier)
                  .undo(),
            ),
            IconButton(
              icon: const Icon(Icons.redo),
              onPressed: () => ref
                  .read(canvasStateProvider(widget.dashboardId).notifier)
                  .redo(),
            ),
            const VerticalDivider(width: 1),
            IconButton(
              icon: Icon(
                canvasState.snapToGrid ? Icons.grid_on : Icons.grid_off,
              ),
              tooltip: 'Snap to Grid',
              onPressed: () => ref
                  .read(canvasStateProvider(widget.dashboardId).notifier)
                  .toggleSnapToGrid(),
            ),
          ],
          const VerticalDivider(width: 1),
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings / Auto-Refresh',
            onPressed: () => _showSettingsDialog(context),
          ),
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share',
            onPressed: () => _showSharingDialog(context),
          ),
          IconButton(
            icon: Icon(isEditMode ? Icons.visibility : Icons.edit),
            tooltip: isEditMode ? 'Preview Mode' : 'Edit Mode',
            onPressed: () => ref
                .read(canvasStateProvider(widget.dashboardId).notifier)
                .toggleMode(),
          ),
          if (canvasState.isDirty)
            IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Save Canvas',
              onPressed: () async {
                await ref
                    .read(canvasStateProvider(widget.dashboardId).notifier)
                    .saveCanvasState();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Canvas saved successfully')),
                );
              },
            ),
        ],
      ),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.surfaceCanvas, AppColors.surfaceCanvasAlt],
          ),
        ),
        child: ResponsiveLayout(
          builder: (context, responsive, constraints) {
            final padding = AppSurfaceStyles.pagePadding(responsive);
            final gap = AppSurfaceStyles.builderGap(responsive);
            final libraryWidth = AppSurfaceStyles.builderLibraryWidth(
              responsive,
            );
            final propertiesWidth = AppSurfaceStyles.builderPropertiesWidth(
              responsive,
            );

            return SafeArea(
              child: Padding(
                padding: padding,
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    maxWidth: responsive.isWide
                        ? AppDimensions.builderWideMaxWidth
                        : constraints.maxWidth,
                  ),
                  child: responsive.isMobile
                      ? _buildMobileWorkspace(gap: gap)
                      : responsive.isTablet
                      ? _buildTabletWorkspace(
                          gap: gap,
                          libraryWidth: libraryWidth,
                        )
                      : _buildDesktopWorkspace(
                          gap: gap,
                          libraryWidth: libraryWidth,
                          propertiesWidth: propertiesWidth,
                        ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildMobileWorkspace({required double gap}) {
    return ListView(
      children: [
        _buildHeaderCard(),
        SizedBox(height: gap),
        SizedBox(
          height: 300,
          child: WidgetLibrarySidebar(dashboardId: widget.dashboardId),
        ),
        SizedBox(height: gap),
        SizedBox(
          height: 640,
          child: DashboardCanvas(dashboardId: widget.dashboardId),
        ),
        SizedBox(height: gap),
        SizedBox(
          height: 520,
          child: PropertyPanel(dashboardId: widget.dashboardId),
        ),
      ],
    );
  }

  Widget _buildTabletWorkspace({
    required double gap,
    required double libraryWidth,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildHeaderCard(),
        SizedBox(height: gap),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                width: libraryWidth,
                child: WidgetLibrarySidebar(dashboardId: widget.dashboardId),
              ),
              SizedBox(width: gap),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: DashboardCanvas(dashboardId: widget.dashboardId),
                    ),
                    SizedBox(height: gap),
                    SizedBox(
                      height: 360,
                      child: PropertyPanel(dashboardId: widget.dashboardId),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDesktopWorkspace({
    required double gap,
    required double libraryWidth,
    required double propertiesWidth,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildHeaderCard(),
        SizedBox(height: gap),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                width: libraryWidth,
                child: WidgetLibrarySidebar(dashboardId: widget.dashboardId),
              ),
              SizedBox(width: gap),
              Expanded(child: DashboardCanvas(dashboardId: widget.dashboardId)),
              SizedBox(width: gap),
              SizedBox(
                width: propertiesWidth,
                child: PropertyPanel(dashboardId: widget.dashboardId),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHeaderCard() {
    return Container(
      decoration: AppSurfaceStyles.card(),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Dashboard builder',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Arrange charts, tables, and widgets with responsive side panels and a centered canvas.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.lg),
          Chip(
            label: Text(_dashboard?.name ?? 'Dashboard'),
            visualDensity: VisualDensity.compact,
            backgroundColor: AppColors.surfaceCardAlt,
            side: const BorderSide(color: AppColors.borderSubtle),
          ),
        ],
      ),
    );
  }

  void _showSharingDialog(BuildContext context) {
    if (_dashboard == null) return;
    showDialog(
      context: context,
      builder: (context) => DashboardSharingDialog(
        dashboard: _dashboard!,
        onDashboardUpdated: (updated) {
          setState(() {
            _dashboard = updated;
          });
        },
      ),
    );
  }

  void _showSettingsDialog(BuildContext context) {
    if (_dashboard == null) return;
    showDialog(
      context: context,
      builder: (context) {
        bool autoRefresh = _dashboard!.settings.autoRefresh;
        int interval = _dashboard!.settings.refreshIntervalSeconds;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Dashboard settings'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Enable auto-refresh'),
                    value: autoRefresh,
                    onChanged: (val) {
                      setDialogState(() => autoRefresh = val);
                    },
                  ),
                  if (autoRefresh) ...[
                    const SizedBox(height: AppSpacing.sm),
                    TextFormField(
                      initialValue: interval.toString(),
                      decoration: const InputDecoration(
                        labelText: 'Refresh interval (seconds)',
                      ),
                      keyboardType: TextInputType.number,
                      onChanged: (val) {
                        final parsed = int.tryParse(val) ?? 60;
                        setDialogState(() => interval = parsed);
                      },
                    ),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () async {
                    final service = ref.read(dashboardServiceProvider);
                    final token = ref.read(authTokenProvider);
                    final newSettings = _dashboard!.settings.copyWith(
                      autoRefresh: autoRefresh,
                      refreshIntervalSeconds: interval,
                    );

                    final updated = await service.updateDashboard(
                      dashboardId: _dashboard!.id,
                      settings: newSettings,
                      token: token,
                    );

                    if (!context.mounted) return;
                    setState(() {
                      _dashboard = updated;
                    });
                    _setupAutoRefreshTimer(updated);
                    Navigator.of(context).pop();
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
