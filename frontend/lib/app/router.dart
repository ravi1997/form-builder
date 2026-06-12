import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/presentation/pages/login_page.dart';
import '../features/auth/presentation/pages/register_page.dart';
import '../features/auth/presentation/pages/password_reset_page.dart';
import '../features/home/presentation/pages/home_page.dart';
import '../features/form_builder/presentation/pages/form_builder_page.dart';
import '../features/dashboard_builder/dashboard_builder_page.dart';
import '../features/compliance/presentation/pages/compliance_page.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(
      path: '/',
      builder: (BuildContext context, GoRouterState state) => const HomePage(),
    ),
    GoRoute(
      path: '/admin/compliance',
      builder: (BuildContext context, GoRouterState state) => const CompliancePage(),
    ),
    GoRoute(
      path: '/login',
      builder: (BuildContext context, GoRouterState state) => const LoginPage(),
    ),
    GoRoute(
      path: '/register',
      builder: (BuildContext context, GoRouterState state) => const RegisterPage(),
    ),
    GoRoute(
      path: '/reset-password',
      builder: (BuildContext context, GoRouterState state) => const PasswordResetPage(),
    ),
    GoRoute(
      path: '/form-builder',
      builder: (BuildContext context, GoRouterState state) => const FormBuilderPage(),
    ),
    GoRoute(
      path: '/dashboard-builder/:id',
      builder: (BuildContext context, GoRouterState state) {
        final id = state.pathParameters['id'] ?? 'default_db';
        return DashboardBuilderPage(dashboardId: id);
      },
    ),
  ],
);

