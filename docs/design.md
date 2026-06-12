# Flutter UI Design Documentation

## Visual System

This project uses a mostly light, enterprise SaaS visual language with strong indigo branding, white surfaces, generous spacing, and responsive card-based layouts.

### Documentation Format

The doc is organized the way design-system docs are typically maintained:

- tokens first: colors, typography, spacing, radii, shadows, and breakpoints
- page specs second: purpose, layout, interactions, and state
- visual notes per page: concrete values for spacing, colors, and dimensions

This mirrors common design-token guidance from Material and Flutter: define reusable values, use semantic names where possible, and document adaptive behavior explicitly rather than only showing widget structure.

### Typography

- Primary font family: `GoogleFonts.inter` on most screens.
- Hero titles: `40px` to `56px`, weight `800`.
- Page titles: `20px` to `32px`, weight `700` to `800`.
- Section titles: `16px` to `18px`, weight `700` to `800`.
- Body copy: `14px` to `15px`.
- Helper/meta text: `11px` to `13px`.
- Label text: `14px`, weight `600`.

### Color System

- Brand primary: `#4338CA` / `#2563EB` / indigo variants depending on screen.
- Hero gradient: `#3730A3` -> `#5B21B6`.
- Light backgrounds: `#F8FAFF`, `#F8FAFC`, `#F5F7FB`, `#F9FAFB`.
- White surfaces: `#FFFFFF`.
- Dark text: `#0F172A`, `#111827`.
- Secondary text: `#334155`, `#475569`, `#64748B`.
- Muted text: `#94A3B8`, `#9CA3AF`.
- Borders/dividers: `#E2E8F0`, `#E5E7EB`.
- Success/error accents: `#166534`, `#991B1B`.

### Token Table

| Token Group | Examples Used In This App |
| --- | --- |
| `color.brand.primary` | `#4338CA`, `#2563EB` |
| `color.brand.gradient.start` | `#3730A3` |
| `color.brand.gradient.end` | `#5B21B6` |
| `color.surface.primary` | `#FFFFFF` |
| `color.surface.canvas` | `#F8FAFF`, `#F8FAFC`, `#F5F7FB`, `#F9FAFB` |
| `color.text.primary` | `#0F172A`, `#111827` |
| `color.text.secondary` | `#334155`, `#475569`, `#64748B` |
| `color.text.muted` | `#94A3B8`, `#9CA3AF` |
| `color.border.subtle` | `#E2E8F0`, `#E5E7EB` |
| `color.state.success` | `#166534` |
| `color.state.error` | `#991B1B` |

### Spacing And Radii

- Auth shell padding: `24px` to `40px` depending on screen.
- Card padding: commonly `16px`, `20px`, `24px`, `28px`, or `40px` depending on hierarchy.
- Common spacing steps: `8px`, `12px`, `16px`, `20px`, `24px`, `32px`, `40px`, `48px`, `56px`.
- Radii:
  - small: `8px`
  - medium: `12px`
  - large: `16px`
  - extra large: `20px` to `24px`
  - pill: `999px`

### Spacing Table

| Token Group | Values Seen In Code |
| --- | --- |
| `space.xs` | `4px`, `6px` |
| `space.sm` | `8px`, `10px`, `12px` |
| `space.md` | `16px`, `20px` |
| `space.lg` | `24px`, `28px`, `32px` |
| `space.xl` | `40px`, `48px`, `56px` |
| `layout.pagePadding` | `24px` default, `16px` on narrow auth layouts |

### Surfaces And Shadows

- Auth cards and admin cards use white surfaces with subtle borders and soft shadows.
- Hero panels use saturated gradients and high-contrast white typography.
- Background decoration on auth pages uses large low-opacity gradient orbs plus a dot-grid overlay.

### Responsive Behavior

- Auth layout breakpoint: mobile `<= 480px`, tablet `<= 1024px`, desktop `> 1024px`.
- Register wide layout: `> 1000px`.
- Admin organization split layout: `> 900px`.
- Form builder compact mode: `< 1100px`.
- Many pages wrap content in a centered `ConstrainedBox` to control line length and card width.

### Layout Patterns

| Pattern | Where Used | Notes |
| --- | --- | --- |
| Centered auth card | Login, register, forgot password, OTP | Keeps forms readable and vertically balanced |
| Split hero + form | Login, register | Marketing content appears only on wider screens |
| Centered max-width dashboard | Dashboard, project analysis boards | Content is constrained to avoid overly wide lines |
| Split master/detail | Organization management | Desktop gets a two-panel layout |
| Tabbed workspace | Form dashboard, builder compact mode | Best for dense multi-section workflows |
| Draggable three-pane workspace | Form builder desktop | Field library, canvas, properties |

### Spec Template

Each page section below follows this format:

- `Purpose`
- `Layout`
- `Components`
- `Interactions`
- `Navigation`
- `States`
- `Visual Spec`

This keeps the document consistent and makes it easier to compare screens.

## Route Map

- `/` -> `DashboardPage`
- `/projects/:projectId` -> `ProjectDashboardPage`
- `/projects/:projectId/forms/:formId` -> `FormDashboardPage`
- `/login` -> `LoginScreen`
- `/register` -> `RegisterScreen`
- `/forgot-password` -> `ForgotPasswordScreen`
- `/verify-otp?mobile=...` -> `OtpVerificationScreen`
- `/builder/:formId` -> `FormBuilderPage`
- `/projects/:projectId/forms/:formId/edit` -> `FormBuilderPage`
- `/projects/:projectId/forms/:formId/responses` -> `ResponseListPage`
- `/projects/:projectId/forms/:formId/responses/:responseId` -> `ResponseDetailPage`
- `/form-preview` -> `FormPreviewPage`
- `/projects/:projectId/f/:formId` -> `FormSubmitPage`
- `/projects/:projectId/forms/:formId/analytics` -> `AnalyticsPage`
- `/admin/orgs` -> `OrganizationManagementScreen`
- `/admin/feature-flags` -> `FeatureFlagsScreen`
- `/admin/ai-ops` -> `AIOpsScreen`

## Shared Reusable UI

### `AuthBackground`

Purpose: shared decorative background for auth views.

Layout:

- `Scaffold`
- `Stack`
  - `Positioned` gradient orb top-right
  - `Positioned` gradient orb bottom-left
  - `Positioned` accent orb mid-left
  - `Positioned.fill`
    - `CustomPaint` dot-grid pattern
  - `SafeArea`
    - `child`

Behavior:

- Purely visual.
- No interaction.

### `AuthCardScaffold`

Purpose: shared centered card layout for auth forms.

Layout:

- `AuthBackground`
- `Center`
  - `SingleChildScrollView`
    - `Container`
      - max width constraint 440
      - white card with border/shadow
      - `Padding`
        - `Column`
          - circular icon badge
          - title
          - subtitle
          - supplied `child`

### `AuthTextFormField`

Purpose: standardized labeled input field for auth screens.

Layout:

- `Column`
  - label `Text`
  - `TextFormField`
  - optional helper text

Behavior:

- Supports validator, prefix icon, suffix icon, password masking, and keyboard type.

---

## `LoginScreen`

### 1. Purpose

Authentication entry screen. Supports two login modes:

- email/password
- mobile OTP

Also persists remembered email locally and clears expired tokens on load.

### 2. UI Layout Structure

- `AuthBackground`
- `Center`
  - `SingleChildScrollView`
    - responsive padding
    - desktop layout or stacked layout

#### Desktop Layout

- `ConstrainedBox`
  - `IntrinsicHeight`
    - `Row`
      - `Expanded`
        - `_HeroPanel`
      - `SizedBox`
      - `SizedBox(width: 460)`
        - `_LoginCard`

#### Mobile/Tablet Layout

- `ConstrainedBox(maxWidth: 500)`
  - `Column`
    - `_CompactHero`
    - spacing
    - `_LoginCard`

### 3. UI Components

- Brand/marketing panel
  - logo mark
  - product name `MahaSamgrah Setu`
  - headline text
  - description text
  - trust badges
  - decorative stats chips
- Login card
  - auth mode tabs
  - email input or mobile input
  - password input with visibility toggle
  - remember me checkbox
  - primary login button
  - forgot password link
  - sign up link

### 4. Interactions & Behavior

- Tab switch between email and OTP mode
  - Trigger: tab tap inside `_LoginCard`
  - Effect: updates `_isEmailTab`
  - Animation: `_tabAnimController` forwards/reverses over 220 ms
- Password visibility toggle
  - Trigger: icon button in password field
  - Effect: toggles `_obscurePassword`
- Remember me checkbox
  - Trigger: checkbox change
  - Effect: toggles `_rememberMe`
- Login button
  - Trigger: button tap
  - Effect:
    - validates form
    - stores/clears remembered email in Hive box `credentials_box`
    - if email mode: calls `authController.login(email, password)`
    - if mobile mode: calls `authController.requestOtp(mobile)`
    - on successful OTP request: navigates to `/verify-otp?mobile=<mobile>`
- Forgot password link
  - Trigger: tap
  - Navigation: `/forgot-password`
- Sign up link
  - Trigger: tap
  - Navigation: `/register`
- Auth state listener
  - On error: shows snackbar
  - On successful login: resets form and navigates to `/`

### 5. Navigation Flow

- `/login` -> `/forgot-password`
- `/login` -> `/register`
- `/login` -> `/verify-otp?mobile=...`
- `/login` -> `/`

### 6. Animations & Transitions

- Tab transition animation
  - Trigger: switching auth tab
  - Effect: animates tab state using `CurvedAnimation`
  - Duration: 220 ms

### 7. Conditional / Dynamic UI

- Desktop vs mobile layout chosen by width breakpoint
- Email/password vs mobile OTP fields
- Remembered email prefilled from Hive when `remember_me` is true
- Login button disabled behavior is controlled by loading state from `authController`

### 8. Notes & Edge Cases

- Token expiry is checked on startup via `tokenServiceProvider`.
- OTP path is optimistic: OTP request is made first, then navigation occurs only if auth state does not become error.

---

## `RegisterScreen`

### 1. Purpose

User account creation screen with email/password registration and marketing content on wide layouts.

### 2. UI Layout Structure

- `AuthBackground`
- `Center`
  - `SingleChildScrollView`
    - `IntrinsicHeight`
      - `Row`
        - optional marketing column on wide screens
        - register card

#### Wide Layout Marketing Column

- brand section
- headline
- feature list
  - secure data
  - AI powered
  - high performance

#### Register Card

- `Container`
  - `Form`
    - title
    - subtitle
    - social login row
    - OR divider
    - username field
    - email field
    - mobile field
    - password field
    - confirm password field
    - primary create account button
    - sign in link

### 3. UI Components

- Outlined social buttons
  - Google
  - Apple
- `AuthTextFormField`
  - Username
  - Email
  - Mobile Number
  - Password
  - Confirm Password
- Password visibility icons
- Primary elevated create account button
- Sign in text link

### 4. Interactions & Behavior

- Social buttons
  - Trigger: tap
  - Effect: currently no-op placeholders
- Password visibility toggles
  - Trigger: icon buttons
  - Effect: toggle masked text for password and confirmation fields
- Create Account button
  - Trigger: tap
  - Effect:
    - validates form
    - calls `authController.register(...)`
- Sign in link
  - Trigger: tap
  - Navigation: `/login`
- Auth state listener
  - On success: shows snackbar and navigates to `/login`
  - On error: shows snackbar error

### 5. Navigation Flow

- `/register` -> `/login`

### 6. Animations & Transitions

- None observed beyond standard Flutter button state changes.

### 7. Conditional / Dynamic UI

- Wide-screen marketing column is shown only when width > 1000
- Loading state disables the submit button and swaps button text with a spinner

### 8. Notes & Edge Cases

- Social sign-in is not implemented yet.
- Validation includes basic email and mobile format checks.

---

## `ForgotPasswordScreen`

### 1. Purpose

Password reset request screen that submits the user email and returns to login after success.

### 2. UI Layout Structure

- `Scaffold`
  - `AuthCardScaffold`
    - header icon
    - title
    - subtitle
    - `Form`
      - email text field
      - reset button
      - back-to-login row

### 3. UI Components

- Email `AuthTextFormField`
- `ElevatedButton`
  - label: `Reset Password`
- Back-to-login `GestureDetector`
- Back icon

### 4. Interactions & Behavior

- Reset Password button
  - Trigger: tap
  - Effect:
    - validates email format
    - calls `authController.requestPasswordReset(email)`
    - loading state shows spinner
- Back to Login link
  - Trigger: tap
  - Navigation: `/login`
- Auth state listener
  - On error: snackbar error
  - On success: snackbar success and delayed navigation to `/login` after 2 seconds

### 5. Navigation Flow

- `/forgot-password` -> `/login`

### 6. Animations & Transitions

- Delayed route change after successful reset request
  - Duration: 2 seconds

### 7. Conditional / Dynamic UI

- Button disabled and spinner shown when auth is loading

### 8. Notes & Edge Cases

- Reset success behavior is assumed to be backend-driven and not confirmed locally.

---

## `OtpVerificationScreen`

### 1. Purpose

OTP confirmation screen for mobile login.

### 2. UI Layout Structure

- `Scaffold`
  - transparent `AppBar`
    - back `IconButton`
  - `AuthCardScaffold`
    - header icon
    - title
    - subtitle with mobile number
    - `Column`
      - `Pinput`
      - spacing
      - loading indicator or resend row

### 3. UI Components

- `Pinput` 6-digit code field
- Back `IconButton`
- Resend timer row
- `TextButton` for resend action
- `CircularProgressIndicator` during auth loading

### 4. Interactions & Behavior

- OTP entry completion
  - Trigger: all 6 digits entered
  - Effect: calls `authController.loginWithOtp(mobile, pin)`
- Back button
  - Trigger: tap
  - Navigation: `context.pop()`
- Resend button
  - Trigger: tap when timer hits zero
  - Effect: calls `otpController.resendOtp(widget.mobile)`
- Timer start
  - Trigger: first frame after init
  - Effect: starts resend countdown if timer is 0

### 5. Navigation Flow

- `/verify-otp?mobile=...` -> previous page via back button

### 6. Animations & Transitions

- Pinput focus state styling transitions are implicit Flutter field-state changes.

### 7. Conditional / Dynamic UI

- Resend button disabled while timer > 0
- Loading indicator replaces resend row while auth request is in progress

### 8. Notes & Edge Cases

- Subtitle assumes Indian country code `+91`.

---

## `DashboardPage`

### 1. Purpose

Main project dashboard after authentication. Shows project-level summary, stats, search/filter controls, and project cards. Supports project creation, archiving, and adding forms.

### 2. UI Layout Structure

- `Scaffold`
  - `body`
    - `authState.when`
      - loading state -> centered spinner
      - error state -> `ErrorStateWidget`
      - data state -> dashboard content

#### Dashboard Content

- `RefreshIndicator`
  - `SingleChildScrollView`
    - centered `ConstrainedBox`
      - `Column`
        - hero card
        - stats row or skeleton/error banner
        - projects toolbar
        - conditional projects area

#### Projects Area

- skeleton while loading
- empty state if no matches
- otherwise `GridView.builder`
  - `_ProjectCard` per project

### 3. UI Components

- Hero card
- Stats cards row
- Search input and filter control in toolbar
- Create project button/action
- Project cards
  - title
  - description
  - status
  - counts
  - actions
- Empty state panel
- Loading skeletons

### 4. Interactions & Behavior

- Pull to refresh
  - Trigger: `RefreshIndicator`
  - Effect: refreshes dashboard controller
- Create project
  - Trigger: hero action/button
  - Effect:
    - opens dialog with title, description, help text
    - submits `createProject`
    - refreshes dashboard
- Search/filter
  - Trigger: toolbar input/filter changes
  - Effect: filters project list locally by title/description/status
- Project card tap
  - Trigger: card tap
  - Navigation: `/projects/<projectId>`
- Add form action on project
  - Trigger: project card action
  - Effect: opens dialog and posts to `createProjectForm`
- Archive project action
  - Trigger: project card action
  - Effect: deletes project, then refreshes dashboard
- Auth user null handling
  - If user is null: shows `Redirecting...`

### 5. Navigation Flow

- `/` -> `/projects/:projectId`

### 6. Animations & Transitions

- Standard dialog transitions for create/add form dialogs
- Standard pull-to-refresh indicator animation

### 7. Conditional / Dynamic UI

- Content gated by auth state
- Stats row switches between data, loading skeleton, and error banner
- Project grid changes based on loading and filtered result set
- Grid column count adapts to screen width via `Responsive.cardColumns`

### 8. Notes & Edge Cases

- Project creation payload uses organization ID from authenticated user when available.
- If `dashboardState` is loading, project cards are replaced by skeletons.

---

## `ProjectDashboardPage`

### 1. Purpose

Project-level management page. Loads project metadata and forms from the backend, and exposes project actions plus summary tabs.

### 2. UI Layout Structure

- `Scaffold`
  - `body`
    - desktop-style split or column content
      - header area
      - project hero card
      - action/menu area
      - tabbed content region

### 3. UI Components

- Back navigation/close via browser route pop
- Project hero card
- Tabs
  - Overview
  - Forms summary-related actions
  - member/administration related content is implied by helper methods
- Project action menu
- Dialog-based editors
  - edit project
  - create form
- Activity and recent forms helpers

### 4. Interactions & Behavior

- Project load
  - Trigger: initState
  - Effect: fetches project details from API
- Forms load
  - Trigger: initState
  - Effect: fetches forms for the project
- Edit project
  - Trigger: action in management menu
  - Effect:
    - opens dialog with title/description/help text
    - updates project via API
    - reloads project
- Create form from project
  - Trigger: action in management menu
  - Effect:
    - opens dialog with form metadata
    - preconfigures slug, tags, language defaults, public/template flags
    - posts form create request
    - refreshes project/form data
- Archive project
  - Trigger: action in management menu
  - Effect: deletes project and pops the page
- Refresh all
  - Trigger: action in management menu
  - Effect: reloads both project and forms

### 5. Navigation Flow

- `/projects/:projectId` -> pop back to dashboard
- Project action routes are defined elsewhere for form drill-down

### 6. Animations & Transitions

- Tab transitions are handled by `TabController` and default Flutter tab animations.

### 7. Conditional / Dynamic UI

- `_memberDataMismatch` is set when member data is not a list shape; this is a guard/validation state.
- `_buildActivityItems` conditionally adds a project updated event when `updated_at` exists.
- `_buildRecentForms` normalizes list items into maps.

### 8. Notes & Edge Cases

- This page contains helper methods for features not fully visible in the current snippet; the behavior is inferred from method names and API calls.

---

## `FormDashboardPage`

### 1. Purpose

Form-scoped dashboard that acts as a hub for overview, responses, analytics, and builder access.

### 2. UI Layout Structure

- `Scaffold`
  - `SafeArea`
    - `SingleChildScrollView`
      - centered constrained column
        - top bar row
        - hero card
        - tabs container
        - `TabBarView`

### 3. UI Components

- Back `IconButton`
- Page title text
- `FilledButton.icon`
  - Edit form
- Hero card with project/form IDs
- `TabBar`
  - Overview
  - Responses
  - Analytics
  - Builder
- Tab content cards
- `FilledButton.icon` action buttons inside tab panes

### 4. Interactions & Behavior

- Back button
  - Trigger: tap
  - Effect: `context.pop()`
- Edit form button
  - Trigger: tap
  - Navigation: `/projects/:projectId/forms/:formId/edit`
- Tab switching
  - Trigger: tab tap
  - Effect: switches visible section in `TabBarView`
- Open responses
  - Trigger: button tap
  - Navigation: `/projects/:projectId/forms/:formId/responses`
- Open analytics
  - Trigger: button tap
  - Navigation: `/projects/:projectId/forms/:formId/analytics`
  - Assumption: route target is intended analytics page, but the route path in the router is project-scoped. This looks like a likely inconsistency.

### 5. Navigation Flow

- `/projects/:projectId/forms/:formId` -> `/projects/:projectId/forms/:formId/edit`
- `/projects/:projectId/forms/:formId` -> `/projects/:projectId/forms/:formId/responses`
- `/projects/:projectId/forms/:formId` -> `/projects/:projectId/forms/:formId/analytics`

### 6. Animations & Transitions

- Default Flutter tab animation via `TabController`

### 7. Conditional / Dynamic UI

- No major data-dependent rendering besides route parameter interpolation.

### 8. Notes & Edge Cases

- The form dashboard analytics button should target `/projects/:projectId/forms/:formId/analytics`; the previous hardcoded form-only route was stale.

---

## `FormBuilderPage`

### 1. Purpose

Primary form authoring workspace. Supports field library, canvas editing, section/question property editing, and responsive compact layout behavior.

### 2. UI Layout Structure

- `Scaffold`
  - body uses `formBuilderControllerProvider(controllerKey)` state
  - loading/data branches

#### Compact Layout

- `DefaultTabController(length: 3)`
  - `Column`
    - top bar
    - tab strip
    - `Expanded`
      - `TabBarView`
        - `FieldLibraryWidget`
        - `FormCanvasWidget`
        - `_CompactPropertiesPane`

#### Desktop Layout

- `Column`
  - top bar
  - `Expanded`
    - `Row`
      - left library pane
      - resize handle
      - center canvas
      - optional right resize handle and properties pane

### 3. UI Components

- `FormBuilderTopBar`
- `FieldLibraryWidget`
- `FormCanvasWidget`
- `BulkQuestionPropertiesWidget`
- `FieldPropertiesWidget`
- `FormPropertiesWidget`
- `SectionPropertiesWidget`
- Resizable splitters via `GestureDetector` + `MouseRegion`
- Compact tab navigation

### 4. Interactions & Behavior

- Restore layout preferences
  - Trigger: initState
  - Effect: reads Hive `form_builder_layout_preferences`
- Save layout preferences
  - Trigger: resize drag end
  - Effect: persists panel widths in Hive
- Left panel resize
  - Trigger: horizontal drag on divider
  - Effect: updates `_leftPanelWidth`
- Right panel resize
  - Trigger: horizontal drag on divider
  - Effect: updates `_rightPanelWidth`
- Compact mode tabs
  - Trigger: screen width < 1100
  - Effect: swaps between library, canvas, and properties
- Auto-initialize first question
  - Trigger: controller state becomes available and mode is `question`
  - Effect: if first section exists and has no questions, adds a short text question automatically

### 5. Navigation Flow

- No direct navigation buttons visible in the page body snippet.
- Builder is reached from routes:
  - `/builder/:formId`
  - `/projects/:projectId/forms/:formId/edit`

### 6. Animations & Transitions

- Tab transitions in compact layout are default Flutter tab animations.
- Panel resizing is immediate, not animated.

### 7. Conditional / Dynamic UI

- Compact vs desktop layout based on width < 1100
- Right properties pane visible only when a selection exists:
  - selected question(s)
  - selected form
  - selected section
- `_CompactPropertiesPane` chooses one of:
  - bulk question properties
  - field properties
  - form properties
  - section properties
  - empty prompt

### 8. Notes & Edge Cases

- The page depends heavily on external builder widgets and controller state.
- Panel width persistence is bounded with min/max clamps.

---

## `FormPreviewPage`

### 1. Purpose

Read-only interactive preview of a builder form. Simulates logic, dynamic options, visibility rules, webhook execution, and submission flows without persisting a submission.

### 2. UI Layout Structure

- `Theme`
  - `Scaffold`
    - `AppBar`
      - preview badge
      - language switcher
      - reset button
      - close preview button
    - `Form`
      - `_buildBody(...)`

### 3. UI Components

- Preview mode badge
- `LanguageSwitcher`
- `TextButton.icon` reset
- `TextButton.icon` close preview
- Form content generated by preview utilities
- Internal maps/state for repeat instances, OTP controllers, rich preview mode, dynamic options, and field errors

### 4. Interactions & Behavior

- Reset button
  - Trigger: tap
  - Effect:
    - invalidates preview providers
    - clears step/submission/review state
    - clears dynamic options, webhook cache, and field errors
- Close Preview button
  - Trigger: tap
  - Navigation: `context.pop()`
- Form data changes
  - Trigger: field input changes
  - Effect:
    - runs `FormLogicEngine.evaluate`
    - applies value overrides
    - applies option overrides
    - triggers pending webhooks once per resolved URL/mapping key

### 5. Navigation Flow

- `FormPreviewPage` -> previous page via close button

### 6. Animations & Transitions

- No explicit animation widgets were visible in the inspected snippet.

### 7. Conditional / Dynamic UI

- Preview theme colors are derived from form style or fall back to app defaults
- Visibility map is computed from logic engine output
- Dynamic option overrides can invalidate current selections and reset them to null
- Webhooks are executed only when the resolved URL changes for the same config key

### 8. Notes & Edge Cases

- This page is highly dynamic and relies on utility functions outside the inspected excerpt.
- Behavior is assumed to be preview-only and not submit persisted data.

---

## `FormSubmitPage`

### 1. Purpose

Public form submission page used by respondents to complete and submit a form.

### 2. UI Layout Structure

- data-loading `FutureProvider` branch
  - loading -> centered spinner
  - error -> error scaffold
  - data -> `_buildFormContent`

#### Form Content

- `Theme`
  - `Scaffold`
    - `AppBar`
      - language switcher
      - reset button
      - close button
    - `Form`
      - generated body from form content builder

### 3. UI Components

- `LanguageSwitcher`
- Reset and Close buttons
- Form-driven interactive fields and action buttons
- internal loading/error state tracking for dynamic fields and webhooks

### 4. Interactions & Behavior

- Form load
  - Trigger: route open
  - Effect: `submitFormProvider` fetches the form by project/form ID
- Reset button
  - Trigger: tap
  - Effect:
    - invalidates submission form data
    - clears step/review/submission state
    - clears dynamic options, webhook cache, loading flags, and field errors
- Close button
  - Trigger: tap
  - Navigation: `context.pop()`
- Form data changes
  - Trigger: user input
  - Effect:
    - evaluates logic engine
    - applies autofill/value overrides
    - applies cascading option overrides
    - debounces webhook execution by 500 ms
    - tracks target field loading states

### 5. Navigation Flow

- Public form route: `/projects/:projectId/f/:formId`
- Close button returns to previous route

### 6. Animations & Transitions

- None explicit in snippet beyond standard form and control feedback.

### 7. Conditional / Dynamic UI

- Loading and error states are fully routed through the `FutureProvider`
- Theme colors derive from form style
- Logic engine visibility and required-status control what is rendered and whether fields are required
- Webhook execution is debounced

### 8. Notes & Edge Cases

- This page shares much of the preview logic but is submission-oriented and includes persistence-related controller flows.

---

## `ConditionBuilderPage`

### 1. Purpose

Conditional logic rule editor for a form. Lets users create, toggle, and delete show/hide/require/etc. rules.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
    - title
    - refresh button
  - body
    - loading spinner or
    - `SingleChildScrollView`
      - `Column`
        - rule creator card
        - rules list card

### 3. UI Components

- Text input for rule name
- Dropdown for field to watch
- Dropdown for operator
- Text input for comparison value
- Dropdown for action
- Dropdown for logical operator
- Create Rule button
- Active rules list
  - `Switch` enable/disable
  - action `Chip`
  - delete `IconButton`

### 4. Interactions & Behavior

- Refresh button
  - Trigger: tap
  - Effect: reloads rules
- Create Rule button
  - Trigger: tap
  - Effect:
    - validates required selections
    - builds `Condition`
    - creates rule through `conditionController`
    - clears form and shows success
- Rule toggle switch
  - Trigger: tap
  - Effect: toggles rule enabled state
- Delete icon
  - Trigger: tap
  - Effect: deletes rule

### 5. Navigation Flow

- No route transitions inside the page.

### 6. Animations & Transitions

- Standard switch and list state updates only.

### 7. Conditional / Dynamic UI

- Loading spinner shown while rules load
- Empty-state message shown when no rules exist
- Operator dropdown is grouped by category using `ConditionController.getOperatorsByCategory()`
- Rule card styling changes when rule is disabled

### 8. Notes & Edge Cases

- Selected field and rule type live in local state rather than form validation.

---

## `ResponseListPage`

### 1. Purpose

Placeholder listing page for form submissions.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
  - `Center`
    - descriptive text

### 3. UI Components

- App bar title
- Placeholder text

### 4. Interactions & Behavior

- No interactive controls beyond standard scaffold navigation.

### 5. Navigation Flow

- Route target: `/projects/:projectId/forms/:formId/responses`

### 6. Animations & Transitions

- None.

### 7. Conditional / Dynamic UI

- None beyond static placeholder text.

### 8. Notes & Edge Cases

- Marked as `Coming Soon`.

---

## `ResponseDetailPage`

### 1. Purpose

Placeholder detail page for a single submitted response.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
  - `Center`
    - descriptive text

### 3. UI Components

- App bar title
- Placeholder text

### 4. Interactions & Behavior

- No interactive controls beyond standard scaffold navigation.

### 5. Navigation Flow

- Route target: `/projects/:projectId/forms/:formId/responses/:responseId`

### 6. Animations & Transitions

- None.

### 7. Conditional / Dynamic UI

- None beyond static placeholder text.

### 8. Notes & Edge Cases

- Marked as `Coming Soon`.

---

## `AnalyticsPage`

### 1. Purpose

Placeholder analytics dashboard for a form.

### 2. UI Layout Structure

- `Scaffold`
  - `Center`
    - text

### 3. UI Components

- Static placeholder text

### 4. Interactions & Behavior

- No interactive controls in the current implementation.

### 5. Navigation Flow

- Route target: `/projects/:projectId/forms/:formId/analytics`

### 6. Animations & Transitions

- None.

### 7. Conditional / Dynamic UI

- None.

### 8. Notes & Edge Cases

- Page is a stub and currently does not consume `projectId` or `formId` in the UI.

---

## `ProjectAnalysisBoardsListPage`

### 1. Purpose

Lists analysis boards for a project and provides entry points to board creation and board detail pages.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
    - back button
    - title
  - `SingleChildScrollView`
    - centered constrained `Column`
      - heading section
      - create board button
      - list of mock boards

### 3. UI Components

- Back `IconButton`
- Heading and subtitle text
- `ElevatedButton.icon`
  - `Create Board`
- Board list items
  - icon tile
  - title
  - description
  - node count chip
  - created date
  - chevron icon

### 4. Interactions & Behavior

- Back button
  - Trigger: tap
  - Navigation: `context.pop()`
- Create Board button
  - Trigger: tap
  - Navigation: `/projects/:projectId/analysis-boards/board-101`
  - Assumption: this route is a hardcoded placeholder and not a real create workflow yet.
- Board tile tap
  - Trigger: tap
  - Navigation: `/projects/:projectId/analysis-boards/<boardId>`

### 5. Navigation Flow

- `/projects/:projectId/analysis-boards` -> board detail page
- `/projects/:projectId/analysis-boards` -> hardcoded board creation target

### 6. Animations & Transitions

- Standard `InkWell` ripple feedback

### 7. Conditional / Dynamic UI

- Board list is driven by a local mock list rather than API data.

### 8. Notes & Edge Cases

- This page currently uses mock data and placeholder routing.

---

## `OrganizationManagementScreen`

### 1. Purpose

Admin screen for managing organizations, their status, stats, and organization admin assignments.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
    - refresh button
  - body
    - loading spinner or
    - desktop split layout or mobile stacked layout
  - `FloatingActionButton`

#### Desktop Layout

- `Row`
  - org list
  - divider
  - stats side panel

#### Mobile Layout

- `Column`
  - org list
  - optional stats side panel

### 3. UI Components

- Organization list cards
- Status chips/badges
- Admin email text
- Org action icon buttons
- Floating action button for create organization
- Create organization dialog
- Assign admin dialog
- Side panel for selected org stats

### 4. Interactions & Behavior

- Refresh button
  - Trigger: tap
  - Effect: reloads org list
- Create organization FAB
  - Trigger: tap
  - Effect:
    - opens dialog with name, slug, domain, admin email
    - validates required fields
    - creates org via repository
    - refreshes list
- Assign admin action
  - Trigger: tap on org action
  - Effect:
    - opens email dialog
    - assigns admin through repository
    - refreshes list
- Organization card tap/selection
  - Trigger: tap
  - Effect: selects org and loads stats in side panel
- Status toggle action
  - Trigger: tap
  - Effect: toggles between active and suspended, refreshes stats if selected

### 5. Navigation Flow

- No route transitions inside the page.

### 6. Animations & Transitions

- Standard dialog transitions and Flutter list updates.

### 7. Conditional / Dynamic UI

- Desktop vs mobile layout depends on width > 900
- Empty state when no organizations exist
- Selected org highlights in list
- Status badges change color based on active/suspended state
- Side panel only appears on mobile when an org is selected

### 8. Notes & Edge Cases

- Stats loading is separate from org list loading.

---

## `FeatureFlagsScreen`

### 1. Purpose

Admin feature rollout manager for global flags and per-organization overrides.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
    - refresh button
  - body
    - loading spinner or empty state or `ListView.builder`
      - flag cards
        - top row
        - description
        - overrides section

### 3. UI Components

- Feature flag card
- Global flag `Switch`
- Description text
- Organization overrides section
- `TextButton.icon`
  - `Add Override`
- Override rows
  - organization name
  - enabled/disabled status text
  - delete icon button
- Add override dialog
  - organization dropdown
  - override switch

### 4. Interactions & Behavior

- Refresh button
  - Trigger: tap
  - Effect: reloads flags and organizations
- Global flag switch
  - Trigger: tap
  - Effect: updates global flag state, then refreshes data
- Add Override button
  - Trigger: tap
  - Effect:
    - opens dialog
    - selects organization
    - chooses enabled/disabled value
    - saves override and refreshes data
- Delete override icon
  - Trigger: tap
  - Effect:
    - calls override update with false
    - comment suggests a real delete endpoint may not exist

### 5. Navigation Flow

- No route transitions inside the page.

### 6. Animations & Transitions

- Standard switch and dialog interactions.

### 7. Conditional / Dynamic UI

- Empty state when no flags exist
- Override list only shown when per-org overrides are present
- Add override dialog is blocked if no organizations are available

### 8. Notes & Edge Cases

- The delete icon behavior is an assumed workaround rather than a dedicated delete action.

---

## `AIOpsScreen`

### 1. Purpose

Admin operations page for LoRA fine-tuning status inspection and triggering a training/improvement loop.

### 2. UI Layout Structure

- `Scaffold`
  - `AppBar`
    - refresh button
  - body
    - loading spinner or
    - `SingleChildScrollView`
      - `Column`
        - status overview card
        - controls card

### 3. UI Components

- Status overview card
  - current active cycle
  - target dataset size
  - last execution timestamps
  - last training exit status
  - active task ID
- Controls card
  - cycles text field
  - dataset size text field
  - fast mode switch
  - launch fine-tuning button

### 4. Interactions & Behavior

- Refresh button
  - Trigger: tap
  - Effect: reloads LoRA status
- Fast mode switch
  - Trigger: tap
  - Effect: toggles `_fastMode`
- Launch Fine-Tuning Loop button
  - Trigger: tap
  - Effect:
    - parses cycles and dataset size
    - calls `triggerImprovementLoop`
    - stores returned task ID
    - shows success snackbar
    - refreshes status

### 5. Navigation Flow

- No route transitions inside the page.

### 6. Animations & Transitions

- Standard button/loading state transitions.

### 7. Conditional / Dynamic UI

- Loading spinner while fetching status or running trigger
- Active task ID section only rendered when a task exists
- Exit code text changes color based on success/failure

### 8. Notes & Edge Cases

- Numeric inputs are parsed with fallbacks, so invalid text silently falls back to defaults.

---

## Visual Spec Addendum

### Auth Screens

- `LoginScreen`
  - uses a full-page decorative auth background.
  - desktop layout is a two-column composition with a large marketing panel and a 460px form card.
  - mobile/tablet collapses into a stacked hero plus form card.
  - hero card uses a purple-indigo gradient, white text, and pill badges.
  - form controls use rounded inputs, muted helper text, and brand-blue interactive states.
- `RegisterScreen`
  - uses the shared auth background and a 500px white card.
  - wide layouts add a marketing column with a 56px headline and feature callouts.
  - social buttons are outlined, white, and lightly bordered.
- `ForgotPasswordScreen`
  - uses the shared centered auth card with a 440px max width.
  - primary button is full-width and 48px tall.
- `OtpVerificationScreen`
  - uses a transparent app bar and the shared auth card scaffold.
  - OTP boxes are 56x56 with 12px radius and explicit focus-state border treatment.

| Screen | Layout | Theme / Background | Spacing | Typography | Notes |
| --- | --- | --- | --- | --- | --- |
| `LoginScreen` | desktop split or stacked mobile | `#F8FAFF` auth shell; indigo gradient hero | `16px`-`24px` outer padding; `56px` desktop gap; `32px` vertical card spacing | Inter; 40px-56px hero; 14px labels/body | Uses remembered-email Hive state and auth mode switching |
| `RegisterScreen` | wide marketing column + form card | `#F8FAFF` auth shell; white card | `24px` / `40px` page padding; `48px` feature gaps; `16px` field spacing | Inter; 56px headline; 14px helper labels | Wide layout only above 1000px |
| `ForgotPasswordScreen` | single centered card | white card inside auth shell | `32px` inner spacing; `48px` button height; `24px` between main blocks | Inter; 28px title; 14px helper text | Reset CTA is full width |
| `OtpVerificationScreen` | centered auth card + app bar | white / auth shell | `48px` between OTP and resend row; `8px` action spacing | Inter; 20px OTP digits; 14px resend text | Includes timer-controlled resend state |

### Dashboard And Project Pages

- `DashboardPage`
  - uses a light SaaS dashboard surface with white cards and 24px page padding.
  - content is centered inside a responsive max-width container.
  - project cards are laid out in a responsive grid with 16px gaps.
- `ProjectDashboardPage`
  - uses a subdued white/light background with a dark-to-blue hero banner.
  - tabs sit inside a bordered white container with a soft blue selected state.
- `FormDashboardPage`
  - mirrors the project dashboard style but with a larger 1200px workspace cap.
  - action buttons use filled icon buttons inside tab panels.

| Screen | Layout | Theme / Background | Spacing | Typography | Notes |
| --- | --- | --- | --- | --- | --- |
| `DashboardPage` | responsive centered dashboard + grid | light canvas, white cards | `24px` section gaps; `16px` grid gaps | 20px+ headings; 14px body | Uses refresh, search, and filter controls |
| `ProjectDashboardPage` | project summary with tabs | white/light scaffold; dark-blue hero card | `20px` between major blocks | 32px hero title; 15px metadata | Tabbed project management hub |
| `FormDashboardPage` | form hub with tabbed actions | `#F5F7FB` background; white tabs | `20px` spacing between sections; `12px`-`16px` internal gaps | 20px page title; 18px section text | Links to edit, responses, analytics |

### Builder And Form Runtime Pages

- `FormBuilderPage`
  - uses a darker builder surface via `AppColors.builderBackground` and sidebar surfaces.
  - desktop layout is a three-pane workspace with draggable dividers.
  - compact layout switches to tabs for library, canvas, and properties.
- `FormPreviewPage`
  - theme colors are derived from the form style.
  - preview badge is a tinted pill in the app bar.
- `FormSubmitPage`
  - shares the preview visual system but is submission-focused.
  - app bar is white with a bottom divider and muted text-icon actions.
- `ConditionBuilderPage`
  - standard Material scaffold with cards, form fields, and action chips.
  - disabled rules are visually dimmed.

| Screen | Layout | Theme / Background | Spacing | Typography | Notes |
| --- | --- | --- | --- | --- | --- |
| `FormBuilderPage` | split-pane desktop; 3-tab compact mode | `AppColors.builderBackground`; builder sidebar surfaces | left `300px`/right `320px` default; divider handles are 1px | dense workspace text; app theme driven | Draggable panes and responsive mode switching |
| `FormPreviewPage` | single form canvas with preview app bar | form style-derived colors; preview badge | app bar control gap `8px`; body driven by form layout | 12px badge; form content inherits style tokens | Reset, close, and language switch are in app bar |
| `FormSubmitPage` | submission flow canvas with app bar | form style-derived colors; white app bar | app bar control gap `8px`; body driven by form layout | matches preview scale; submission-focused | Debounced logic/webhook flow |
| `ConditionBuilderPage` | scrollable rule builder cards | standard Material scaffold | `16px` field spacing; `24px` between cards | 14px labels; large card titles | Uses dropdowns, switch, chip, and delete actions |

### Admin And Utility Pages

- `OrganizationManagementScreen`
  - uses a soft slate background, white cards, and a split layout on desktop.
  - active/suspended states are encoded with green/red chips.
- `FeatureFlagsScreen`
  - uses white cards with light borders and brand-purple switches.
- `AIOpsScreen`
  - uses white cards on a pale slate background with bold section headings.
- `ProjectAnalysisBoardsListPage`
  - uses a clean `#F9FAFB` background and indigo accent cards.
- `AnalyticsPage`, `ResponseListPage`, and `ResponseDetailPage`
  - are explicit stub pages with minimal scaffold styling.

| Screen | Layout | Theme / Background | Spacing | Typography | Notes |
| --- | --- | --- | --- | --- | --- |
| `OrganizationManagementScreen` | desktop split / mobile stacked | `#F8FAFC`; white cards | `16px` list gaps; `24px` page padding | 16px titles; 12px meta | Selected-org side panel on desktop |
| `FeatureFlagsScreen` | list of flag cards + override dialogs | `#F8FAFC`; bordered white cards | `24px` card gap; `8px` switch/text spacing | 16px flag title; 12px key text | Global switch + per-org overrides |
| `AIOpsScreen` | stacked status + controls cards | `#F8FAFC`; bordered white cards | `24px` between cards; `16px` field spacing | 16px headers; 14px labels | Launch action writes task ID state |
| `ProjectAnalysisBoardsListPage` | scrollable list with CTA | `#F9FAFB`; indigo-accent cards | `32px` top spacing; `16px` list gaps | 28px title; 13px body | Uses mock boards and hardcoded navigation |
| `AnalyticsPage` / `ResponseListPage` / `ResponseDetailPage` | centered stub scaffold | default scaffold | minimal | no custom hierarchy | Explicit placeholder pages, no custom visual system beyond base Flutter |

## Page Spec Schema

Use this template for each screen section in this document and for future additions:

| Section | What It Should Contain |
| --- | --- |
| `Purpose` | The user/job-to-be-done for the page |
| `Layout` | Widget hierarchy, container structure, and major regions |
| `Components` | All interactive and visual elements, including reused widgets |
| `Interactions` | Every button, tap target, input, state change, and callback |
| `Navigation` | Source-to-target page transitions and route params |
| `States` | Loading, empty, error, disabled, selected, and conditional rendering |
| `Visual Spec` | Colors, spacing, radii, typography, surfaces, shadows, and responsive rules |

## Normalized Spec Order

All page and widget entries in this document should be interpreted in the same order below. If a section is missing, it means the code did not expose a meaningful value for it or the feature is a stub.

1. Purpose
2. Layout
3. Components
4. Interactions
5. Navigation
6. States
7. Visual Spec

## Widget Spec Schema

Use this template for reusable widgets, dialogs, and shared components:

| Section | What It Should Contain |
| --- | --- |
| `Purpose` | What the widget solves or encapsulates |
| `Layout` | Internal structure, constraints, and container hierarchy |
| `Components` | The controls, fields, text, icons, and repeated sub-elements |
| `Interactions` | Gestures, callbacks, state changes, and actions |
| `Navigation` | Any route changes or modal open/close behavior |
| `States` | Loading, enabled, disabled, selected, empty, and error states |
| `Visual Spec` | Exact colors, spacing, radii, typography, borders, shadows, and breakpoints |

## Component Inventory Rules

- Document reused components separately when they appear across multiple pages.
- List every button, text input, switch, dropdown, chip, icon button, and gesture target.
- Call out icon-only actions even when they are purely visual controls.
- If a component is data-driven, mark it as runtime-generated or API-driven.
- If a component is a placeholder, explicitly label it as a stub.

## State And Behavior Rules

- Always document loading, success, error, empty, and disabled states.
- If a page depends on local state, name the state fields and the conditions that change them.
- If a page depends on external providers, repositories, or APIs, note the dependency.
- If a layout changes by breakpoint, document the threshold and the resulting layout swap.

## Detailed Widget Style Inventory

This section captures reusable widget styling and higher-fidelity CSS-like details for shared controls and workspace widgets.

### `AuthBackground`

| Property | Value |
| --- | --- |
| Base background | `#F8FAFF` |
| Top-right orb | `550px`, radial gradient `#4F46E5` -> transparent, opacity `0.055` |
| Bottom-left orb | `440px`, radial gradient `#7C3AED` -> transparent, opacity `0.045` |
| Mid-left orb | `260px`, radial gradient `#6366F1` -> transparent, opacity `0.03` |
| Dot grid spacing | `28px` |
| Dot size | `1.5px` radius |
| Dot grid opacity | `0.35` overall, individual dots at `0.06` alpha |

### `AuthCardScaffold`

| Property | Value |
| --- | --- |
| Card max width | `440px` |
| Outer padding | `24px` |
| Inner padding | `32px` horizontal, `48px` vertical |
| Background | `#FFFFFF` |
| Border | `1.5px solid AppColors.borderLight` |
| Border radius | `16px` |
| Shadow | soft black shadow with `0.05` alpha |
| Header icon size | `32px` |
| Header icon container | `16px` padding, circular, tinted primary background |
| Title size | `28px`, bold |
| Subtitle size | `14px` |
| Subtitle color | `AppColors.textGrey` |

### `AuthTextFormField`

| Property | Value |
| --- | --- |
| Label size | `14px`, weight `600` |
| Label color | `AppColors.textDark` |
| Spacing between label and field | `8px` |
| Field text size | `14px` |
| Field fill | `AppColors.fieldBackground` |
| Field hint size | `14px` |
| Field hint color | `Colors.grey[400]` |
| Field corner radius | `8px` |
| Field border | `1px` light gray |
| Focus border | `AppColors.brandBlue`, `1.5px` |
| Prefix icon size | `18px` |
| Prefix icon color | `AppColors.textGrey` at `0.7` alpha |
| Helper text size | `12px` |
| Helper text color | `AppColors.textGrey` |

### `LoginScreen` Styling

| Element | Value |
| --- | --- |
| Desktop hero panel radius | `24px` |
| Desktop hero padding | `48px` horizontal, `56px` vertical |
| Desktop hero gradient | `#3730A3` -> `#5B21B6` |
| Compact hero radius | `16px` to `24px` |
| Compact hero padding | `20px`-`32px` horizontal, `28px`-`36px` vertical |
| Trust badge radius | `999px` |
| Trust badge fill | translucent white `0.15` |
| Trust badge dot | `6px` green dot |
| Hero headline size | `40px` |
| Hero headline weight | `800` |
| Hero body size | `15px` |
| Login card width | `460px` |

### `RegisterScreen` Styling

| Element | Value |
| --- | --- |
| Marketing headline size | `56px` |
| Marketing headline weight | `800` |
| Marketing headline color | `#111827` |
| Feature icon tile | light blue background, `8px` radius, `8px` padding |
| Register card width | `500px` |
| Register card padding | `40px` |
| Register card radius | `16px` |
| Register card border | `1px solid #E5E7EB` |
| Social button style | outlined, white background, gray border, `8px` radius |

### `FormBuilderTopBar`

| Property | Value |
| --- | --- |
| Top bar height | `64px` |
| Background | `AppColors.builderSidebar` |
| Bottom border | `1px solid AppColors.builderBorder` |
| Horizontal padding | `16px` |
| Back button icon color | `AppColors.textGrey` |
| Title style | `Theme.of(context).textTheme.titleLarge`, bold, `AppColors.textDark` |
| Version badge background | `AppColors.primary` at `0.1` alpha |
| Version badge radius | `4px` |
| Editing badge background | green at `0.1` alpha |
| Editing badge radius | `4px` |
| Unsaved badge | orange tint with pill radius `999px` |
| Undo/redo button style | `TextButton.icon` with disabled state tied to `canUndo` / `canRedo` |
| Save button height | `36px` |
| Save button radius | `8px` |
| Publish button background | `AppColors.primary` |
| Publish button radius | `8px` |
| Merge & Sync action | icon branch button, `13px` label |
| Preview action | icon eye button |

### `FormCanvasWidget`

| Property | Value |
| --- | --- |
| Canvas padding | `32px` |
| Canvas background | parsed from form style; fallback `AppColors.builderCanvas` |
| Title block padding | `16px` vertical, `24px` horizontal |
| Title block radius | `8px` |
| Title block fill | white |
| Title shadow | black at `0.05` alpha, blur `10`, offset `0,4` |
| Empty state padding | `80px` vertical |
| Empty state title size | `20px` |
| Empty state subtitle size | `15px` |
| Empty state border radius | `16px` dashed region |
| Section spacing | `24px` |
| Section layout | 1, 2, or 3 columns based on form layout and available width |
| Section card gap | `24px` run spacing and spacing |

### `FieldLibraryWidget`

| Property | Value |
| --- | --- |
| Search field text size | `14px` |
| Search hint size | `13px` |
| Search field fill | `AppColors.builderBackground` |
| Search field radius | `10px` |
| Search field border | transparent default, `AppColors.primary` with `0.3` alpha on focus |
| Category tab label size | `13px` |
| Tab label colors | active `AppColors.brandBlue`, inactive `AppColors.textGrey` |
| Item tile size | `105px` wide, `85px` high |
| Item tile radius | `12px` |
| Item tile border | `1px` or `1.5px` depending on custom field state |
| Item tile shadow | light shadow with `0.05` alpha |
| Item icon tile | `8px` padding, tinted icon background |
| Item title size | `11px` |
| Item title color | `AppColors.textDark` |

### `OrganizationManagementScreen`

| Property | Value |
| --- | --- |
| Page background | `#F8FAFC` |
| App bar background | `#FFFFFF` |
| App bar elevation | `0` |
| Card radius | `12px` |
| Card border | `1px solid #E2E8F0` |
| Selected card border | `2px solid #4338CA` |
| Status pill radius | `999px` |
| Status pill padding | `8px` horizontal, `2px` vertical |
| FAB color | `#4338CA` |
| Status chip colors | green for active, red for suspended |

### `FeatureFlagsScreen`

| Property | Value |
| --- | --- |
| Page background | `#F8FAFC` |
| Card radius | `16px` |
| Card border | `1px solid #E2E8F0` |
| Card padding | `20px` |
| Switch accent | `#4338CA` |
| Override row spacing | `8px` to `16px` |
| Add Override button color | `#4338CA` |

### `AIOpsScreen`

| Property | Value |
| --- | --- |
| Page background | `#F8FAFC` |
| App bar background | `#FFFFFF` |
| Card radius | `16px` |
| Card border | `1px solid #E2E8F0` |
| Card padding | `24px` |
| Primary button height | `48px` |
| Primary button radius | `8px` |
| Switch thumb color | `#4338CA` |

### `ProjectAnalysisBoardsListPage`

| Property | Value |
| --- | --- |
| Page background | `#F9FAFB` |
| Page padding | `48px` horizontal, `32px` vertical |
| Card radius | `12px` |
| Card border | `1px solid #E5E7EB` |
| Card shadow | subtle black shadow at `0.02` alpha |
| Accent color | `#6366F1` |
| Title size | `28px` |
| Body size | `13px` |

## Form Builder Subwidget Style Inventory

### `SectionWidget`

| Property | Value |
| --- | --- |
| Section container margin | `24px` bottom |
| Section shell type | `Material` with `sectionStyle.elevation` |
| Section background | parsed from `sectionStyle.backgroundColor`, fallback white |
| Border radius | `sectionStyle.borderRadius` |
| Border width | `sectionStyle.borderWidth` or metadata override |
| Border color | parsed from section style or `AppColors.borderLight` |
| Selected/hover border | `AppColors.primary`, `2px` |
| Header padding | `24px` |
| Header background | parsed from `sectionStyle.headerBackgroundColor`, fallback `AppColors.builderElement` at `0.5` alpha |
| Header border bottom | `1px solid AppColors.borderLight` |
| Section title size | style-driven or default section title text size from metadata |
| Field gap | metadata `fieldGap` or `16px` default |
| Vertical padding | metadata `verticalPadding` or `sectionStyle.padding` |
| Horizontal padding | metadata `horizontalPadding` or `sectionStyle.padding` |
| Alignment | left/center/right from metadata |
| Max width | metadata `maxWidth` or `760px` for centered layout, `1200px` otherwise |
| Empty section title | `20px` |
| Empty section subtitle | `15px` |
| Empty section padding | `80px` vertical |

### `FieldPropertiesWidget`

| Property | Value |
| --- | --- |
| Panel wrapper | `PropertiesPanelShell` |
| Header padding | `16px` |
| Header icon | sliders icon, `16px` |
| Header title size | `16px` |
| Header title weight | bold |
| Save Template action | `TextButton.icon`, label `12px`, icon `16px` |
| Close action | `IconButton`, icon `20px` |
| Form field controllers | label, variable name, helper text, placeholder, regex, min/max length, min/max value, input mask, custom error, prefix icon, suffix icon |
| Panel type | tabbed properties panel with form/field-specific tabs from imported subpanels |

### `FormPropertiesWidget`

| Property | Value |
| --- | --- |
| Panel wrapper | `PropertiesPanelShell` |
| Header padding | `16px` |
| Header icon | file-lines icon, `16px` |
| Header title size | `16px` |
| Editing language strip | `12px` text, `14px` translate icon, `16px`/`8px` padding |
| Language selector | dense dropdown, primary-colored bold `12px` text |
| Tab bar | 5 tabs, label size `13px`, weight bold, indicator `3px` |
| Tab labels | General, Layout, Style, Logic, Access & Security |
| Background tint strip | `AppColors.builderBackground` with `0.5` alpha |

### `SectionPropertiesWidget`

| Property | Value |
| --- | --- |
| Panel wrapper | `PropertiesPanelShell` |
| Header padding | `16px` |
| Header icon | layer-group icon, `16px` |
| Header title size | `16px` |
| Tab bar | 4 tabs, scrollable, label size `13px`, indicator `3px` |
| Header close action | `IconButton`, icon `20px` |
| Supported tabs | General, Layout, Style, Logic |

### `BulkQuestionPropertiesWidget`

| Property | Value |
| --- | --- |
| Container background | white |
| Left border | `1px solid AppColors.borderLight` |
| Header padding | `16px` |
| Header icon | layers-outline icon |
| Header title size | `16px` |
| Common changes label | `12px`, bold, uppercase, letter-spaced |
| Scroll content padding | `20px` |
| Dropdown fill | `AppColors.builderElement` |
| Dropdown border | `OutlineInputBorder` with `AppColors.borderLight`; focused `AppColors.primary` |
| Section gap between controls | `12px` |
| Close action | `IconButton`, text-grey icon |

### `FormBuilderTopBar` Actions

| Element | Value |
| --- | --- |
| Generic top-bar action button | `TextButton`-like custom control with icon `14px`, label `13px`, horizontal padding `12px`, vertical padding `12px` |
| Save button | `36px` height, `8px` radius, primary background when active, muted when saving |
| Publish button | `48px` padding horizontally `20px`, vertically `16px`, primary background |
| Version badge | `4px` radius, `12px` font |
| Editing badge | `4px` radius, `12px` font |
| Unsaved changes badge | pill, orange tint, `12px` font |

### `Build Primary Form Action Button`

| Property | Value |
| --- | --- |
| Base alignment | centered |
| Background color | supplied `primaryColor` |
| Foreground color | white |
| Horizontal padding | `48px` normal, `32px` small |
| Vertical padding | `16px` normal, `12px` small |
| Border radius | supplied parameter |
| Text style | `16px`, bold |

### `Dialogs`

#### `PublishSuccessDialog`

| Property | Value |
| --- | --- |
| Dialog radius | `16px` |
| Padding | `24px` |
| Success icon container | `80px` circle |
| Success icon | check icon, `40px`, green |
| Title size | `24px` |
| Subtitle size | `16px` |
| Link box padding | `16px` horizontal, `12px` vertical |
| Link box radius | `8px` |
| QR container padding | `16px` |
| QR container radius | `12px` |
| QR size | `160px` |
| Done button padding | `16px` vertical |
| Done button radius | `8px` |

#### `GitMergeDialog`

| Property | Value |
| --- | --- |
| Blur | `sigmaX 8`, `sigmaY 8` |
| Dialog background | white with `0.88` alpha |
| Elevation | `24` |
| Radius | `20px` |
| Width | `85%` of screen |
| Height | `80%` of screen |
| Inner padding | `24px` |
| Header icon size | `24px` |
| Header title | theme headline medium, bold |
| Description size | `14px` |
| Conflict card margin | `16px` bottom |
| Conflict card radius | `12px` |
| Conflict card padding | `16px` |
| Path chip | `4px` radius, monospace, bold |
| Comparison pane padding | `12px` |
| Comparison pane radius | `8px` |
| Selected pane highlight | `AppColors.primary` with `0.08` alpha |
| Button-like resolution panes | `1.5px` border |

#### `AiAssistantDialog`

| Property | Value |
| --- | --- |
| Dialog radius | `20px` |
| Dialog size | `500px` by `600px` |
| Padding | `24px` |
| Header title font | `GoogleFonts.outfit` |
| Header title size | `24px` |
| Tab bar | 3 tabs, primary active color, label-sized indicator |
| Prompt field fill | `AppColors.builderBackground` |
| Prompt field radius | `12px` |
| Prompt field focus border | `AppColors.primary`, `2px` |
| Generate button padding | `16px` vertical |
| Generate button radius | `12px` |
| Suggestions card padding | `16px` |
| Suggestions card radius | `12px` |
| Suggestions badge radius | `4px` |
| Suggestions badge font | `10px` |

#### `WorkflowConfigurationDialog`

| Property | Value |
| --- | --- |
| Variable picker title size | `18px` |
| Variable picker radius | `12px` |
| Variable picker max width | `400px` |
| Variable picker max height | `400px` |
| List tile leading tile | `6px` padding, primary-tinted background, `6px` radius |
| Variable label size | `13px` |
| Variable subtitle size | `11px` |
| Variable helper action | icon button with primary icon color |

#### `TemplatePreviewDialog`

| Property | Value |
| --- | --- |
| Dialog max width | `800px` |
| Dialog max height | `600px` |
| Header padding | `20px` |
| Header border bottom | `1px solid #E5E7EB` |
| Template title size | `20px` |
| Category chip radius | `4px` |
| Category chip padding | `8px` horizontal, `4px` vertical |
| Tag chip radius | `16px` |
| Tag chip padding | `12px` horizontal, `6px` vertical |
| Preview card background | `#F9FAFB` |
| Preview card radius | `8px` |
| Preview card border | `1px solid #E5E7EB` |
| Footer border top | `1px solid #E5E7EB` |
| Cancel button radius | `8px` |
| Use button radius | `8px` |

#### `LogicRuleDialog`

| Property | Value |
| --- | --- |
| Dialog width | `600px` |
| Dialog height | `400px` |
| Padding | `16px` |
| Title size | `20px` |
| Title weight | bold |
| Body text | centered placeholder |
| Footer actions | cancel text button, save elevated button |

#### `CameraCaptureDialog`

| Property | Value |
| --- | --- |
| Style details | not fully visible in the inspected excerpt |
| Assumed role | camera/photo capture modal for media questions |
| Confidence | medium due to partial snippet only |

#### `SignaturePadWidget`

| Property | Value |
| --- | --- |
| Style details | not fully visible in the inspected excerpt |
| Assumed role | signature capture canvas and toolbar controls |
| Confidence | medium due to partial snippet only |
