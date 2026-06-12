import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../../../core/widgets/responsive.dart';
import '../../providers/form_builder_provider.dart';
import '../widgets/canvas.dart';
import '../widgets/elements_panel.dart';
import '../widgets/properties_panel.dart';

class FormBuilderPage extends ConsumerStatefulWidget {
  const FormBuilderPage({super.key});

  @override
  ConsumerState<FormBuilderPage> createState() => _FormBuilderPageState();
}

class _FormBuilderPageState extends ConsumerState<FormBuilderPage> {
  String _activeSubSectionId = 'subsec_1';
  bool _showPropertiesPanel = true;
  ProviderSubscription<FormBuilderState>? _selectionSubscription;

  @override
  void initState() {
    super.initState();
    _selectionSubscription = ref.listenManual<FormBuilderState>(
      formBuilderProvider,
      (previous, next) {
      if (next.selectedElementId != null && !_showPropertiesPanel) {
        setState(() {
          _showPropertiesPanel = true;
        });
      }
      },
    );
  }

  @override
  void dispose() {
    _selectionSubscription?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.builderBackground,
      appBar: AppBar(
        title: const Text('Form Builder'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    'Select a sub-section, then add fields from the library.',
                  ),
                ),
              );
            },
          ),
          const SizedBox(width: AppSpacing.xs),
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
            final libraryWidth = AppSurfaceStyles.builderLibraryWidth(
              responsive,
            );
            final propertiesWidth = AppSurfaceStyles.builderPropertiesWidth(
              responsive,
            );
            final gap = AppSurfaceStyles.builderGap(responsive);

            final workspace = responsive.isMobile
                ? _buildMobileWorkspace(
                    context: context,
                    padding: padding,
                    gap: gap,
                  )
                : responsive.isTablet
                ? _buildTabletWorkspace(
                    context: context,
                    padding: padding,
                    gap: gap,
                    libraryWidth: libraryWidth,
                  )
                : _buildDesktopWorkspace(
                    context: context,
                    padding: padding,
                    gap: gap,
                    libraryWidth: libraryWidth,
                    propertiesWidth: propertiesWidth,
                  );

            return SafeArea(
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    maxWidth: responsive.isWide
                        ? AppDimensions.builderWideMaxWidth
                        : constraints.maxWidth,
                  ),
                  child: workspace,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildMobileWorkspace({
    required BuildContext context,
    required EdgeInsets padding,
    required double gap,
  }) {
    return ListView(
      padding: padding,
      children: [
        _buildWorkspaceHeader(context),
        SizedBox(height: gap),
        SizedBox(
          height: 340,
          child: ElementsPanel(activeSubSectionId: _activeSubSectionId),
        ),
        SizedBox(height: gap),
        SizedBox(
          height: 620,
          child: BuilderCanvas(
            activeSubSectionId: _activeSubSectionId,
            onSubSectionActivated: (id) {
              setState(() {
                _activeSubSectionId = id;
              });
            },
          ),
        ),
        SizedBox(height: gap),
        _showPropertiesPanel
            ? SizedBox(
                height: 420,
                child: PropertiesPanel(
                  onClosePanel: () {
                    setState(() {
                      _showPropertiesPanel = false;
                    });
                  },
                ),
              )
            : const SizedBox.shrink(),
      ],
    );
  }

  Widget _buildTabletWorkspace({
    required BuildContext context,
    required EdgeInsets padding,
    required double gap,
    required double libraryWidth,
  }) {
    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildWorkspaceHeader(context),
          SizedBox(height: gap),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(
                  width: libraryWidth,
                  child: ElementsPanel(activeSubSectionId: _activeSubSectionId),
                ),
                SizedBox(width: gap),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: BuilderCanvas(
                          activeSubSectionId: _activeSubSectionId,
                          onSubSectionActivated: (id) {
                            setState(() {
                              _activeSubSectionId = id;
                            });
                          },
                        ),
                      ),
                      SizedBox(height: gap),
                      _showPropertiesPanel
                          ? SizedBox(
                              height: 360,
                              child: PropertiesPanel(
                                onClosePanel: () {
                                  setState(() {
                                    _showPropertiesPanel = false;
                                  });
                                },
                              ),
                            )
                          : const SizedBox.shrink(),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDesktopWorkspace({
    required BuildContext context,
    required EdgeInsets padding,
    required double gap,
    required double libraryWidth,
    required double propertiesWidth,
  }) {
    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildWorkspaceHeader(context),
          SizedBox(height: gap),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(
                  width: libraryWidth,
                  child: ElementsPanel(activeSubSectionId: _activeSubSectionId),
                ),
                SizedBox(width: gap),
                Expanded(
                  child: BuilderCanvas(
                    activeSubSectionId: _activeSubSectionId,
                    onSubSectionActivated: (id) {
                      setState(() {
                        _activeSubSectionId = id;
                      });
                    },
                  ),
                ),
                SizedBox(width: gap),
                _showPropertiesPanel
                    ? SizedBox(
                        width: propertiesWidth,
                        child: PropertiesPanel(
                          onClosePanel: () {
                            setState(() {
                              _showPropertiesPanel = false;
                            });
                          },
                        ),
                      )
                    : const SizedBox.shrink(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWorkspaceHeader(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Form authoring workspace',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    'Use the library to add fields, the canvas to organize sections, and the properties panel to edit the selected element.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.lg),
            Chip(
              avatar: const Icon(Icons.track_changes, size: 18),
              label: Text('Active: $_activeSubSectionId'),
              visualDensity: VisualDensity.compact,
              side: const BorderSide(color: AppColors.borderSubtle),
              backgroundColor: AppColors.surfaceCardAlt,
            ),
          ],
        ),
      ),
    );
  }
}
