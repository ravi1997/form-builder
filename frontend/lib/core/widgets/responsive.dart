import 'package:flutter/material.dart';

import '../theme/design_system.dart';

typedef ResponsiveWidgetBuilder =
    Widget Function(
      BuildContext context,
      AppResponsiveInfo responsive,
      BoxConstraints constraints,
    );

class ResponsiveLayout extends StatelessWidget {
  final ResponsiveWidgetBuilder builder;

  const ResponsiveLayout({super.key, required this.builder});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final responsive = AppResponsiveInfo.fromWidth(constraints.maxWidth);
        return builder(context, responsive, constraints);
      },
    );
  }
}
