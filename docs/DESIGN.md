---
version: alpha
name: Aetheris AI
description: Neutral editorial design system for the Aetheris AI Flutter app, covering auth, dashboards, form builder, runtime forms, and admin surfaces.
colors:
  brand.primary: "#3949AB"
  brand.primary-strong: "#273592"
  brand.primary-soft: "#E8ECF8"
  brand.gradient-start: "#4A5568"
  brand.gradient-end: "#6B7280"
  surface.canvas: "#FAF8F5"
  surface.canvas-alt: "#F5F1EA"
  surface.card: "#FFFDF9"
  surface.card-alt: "#F8F4EE"
  text.primary: "#111827"
  text.secondary: "#374151"
  text.muted: "#6B7280"
  text.subtle: "#9CA3AF"
  border.subtle: "#DDD6C9"
  border.strong: "#D6D0C5"
  state.success: "#166534"
  state.warning: "#B45309"
  state.error: "#991B1B"
  state.info: "#3949AB"
typography:
  display-lg:
    fontFamily: "Inter"
    fontSize: "56px"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  display-md:
    fontFamily: "Inter"
    fontSize: "40px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline-lg:
    fontFamily: "Inter"
    fontSize: "32px"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  headline-md:
    fontFamily: "Inter"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  headline-sm:
    fontFamily: "Inter"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body-lg:
    fontFamily: "Inter"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0em"
  body-md:
    fontFamily: "Inter"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0em"
  label-lg:
    fontFamily: "Inter"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0em"
  label-sm:
    fontFamily: "Inter"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "0.04em"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  full: "999px"
spacing:
  0: "0px"
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  7: "28px"
  8: "32px"
  10: "40px"
  12: "48px"
  14: "56px"
  16: "64px"
elevation:
  none:
    shadow: "none"
  sm:
    shadow: "0 1px 2px rgba(15, 23, 42, 0.06)"
  md:
    shadow: "0 4px 10px rgba(15, 23, 42, 0.08)"
  lg:
    shadow: "0 10px 20px rgba(15, 23, 42, 0.10)"
  xl:
    shadow: "0 20px 40px rgba(15, 23, 42, 0.12)"
components:
  button-primary:
    backgroundColor: "{colors.brand.primary}"
    textColor: "{colors.surface.card}"
    paddingX: "{spacing.6}"
    paddingY: "{spacing.4}"
    rounded: "{rounded.sm}"
    typography: "{typography.label-lg}"
    hoverBackgroundColor: "{colors.brand.primary-strong}"
    activeBackgroundColor: "{colors.brand.primary-strong}"
    disabledBackgroundColor: "{colors.text.subtle}"
    disabledTextColor: "{colors.surface.card}"
  button-secondary:
    backgroundColor: "{colors.surface.card}"
    textColor: "{colors.text.primary}"
    paddingX: "{spacing.6}"
    paddingY: "{spacing.4}"
    rounded: "{rounded.sm}"
    typography: "{typography.label-lg}"
    borderColor: "{colors.border.subtle}"
    hoverBackgroundColor: "{colors.surface.card-alt}"
    disabledBackgroundColor: "{colors.surface.card}"
    disabledTextColor: "{colors.text.subtle}"
  card:
    backgroundColor: "{colors.surface.card}"
    textColor: "{colors.text.primary}"
    padding: "{spacing.6}"
    rounded: "{rounded.lg}"
    elevation: "{elevation.sm}"
    borderColor: "{colors.border.strong}"
  input:
    backgroundColor: "{colors.surface.card-alt}"
    textColor: "{colors.text.primary}"
    paddingX: "{spacing.4}"
    paddingY: "{spacing.3}"
    rounded: "{rounded.sm}"
    typography: "{typography.body-md}"
    borderColor: "{colors.border.subtle}"
    focusBorderColor: "{colors.brand.primary}"
    placeholderColor: "{colors.text.subtle}"
    disabledBackgroundColor: "{colors.surface.card-alt}"
  list-item:
    backgroundColor: "{colors.surface.card}"
    textColor: "{colors.text.primary}"
    paddingX: "{spacing.5}"
    paddingY: "{spacing.4}"
    rounded: "{rounded.md}"
    typography: "{typography.body-md}"
    borderColor: "{colors.border.strong}"
    hoverBackgroundColor: "{colors.surface.card-alt}"
---

## Overview (Brand & Style)

Aetheris AI is an internal, self-hosted platform for teams. The visual tone is trustworthy, structured, and utility-first: warm neutral surfaces, dark ink-like text, restrained shadows, and minimal gradient usage. Indigo is present as a disciplined accent for active states, links, and important actions, not as the primary visual language. The product serves operational teams, admins, and form builders, so the UI must support both dense configuration work and lightweight respondent experiences.

Design principles:
- Prefer calm white or pale slate surfaces over saturated backgrounds.
- Use indigo as the default interactive color and reserve stronger accent states for emphasis.
- Keep forms, tables, and configuration panels readable on desktop and usable on mobile.
- Make hierarchy obvious through typography, spacing, and cards, not decorative clutter.

## Colors

Color is semantic, not decorative.

- `colors.brand.primary` is the main action color for primary buttons, active tabs, focus borders, and key interactive emphasis.
- `colors.brand.primary-strong` is used for hover and active states when stronger contrast is needed.
- `colors.brand.primary-soft` is for subtle highlights, badges, selected states, and tinted surfaces.
- `colors.brand.gradient-start` and `colors.brand.gradient-end` are reserved for rare hero panels; gradients should not dominate the interface.
- `colors.surface.canvas` and `colors.surface.canvas-alt` are the standard page backgrounds and should feel warm, quiet, and paper-like.
- `colors.surface.card` is the default surface for cards, dialogs, and panels.
- `colors.surface.card-alt` is used for inset fields, previews, and muted blocks.
- `colors.text.primary` is used for headings and high-importance content.
- `colors.text.secondary` is used for descriptions and supporting content.
- `colors.text.muted` and `colors.text.subtle` are for helper text, metadata, and inactive controls.
- `colors.border.subtle` and `colors.border.strong` define structural separation without excessive visual weight.
- State colors are limited to status feedback and should not be used as decorative accents.

Accessibility rules:
- Always preserve WCAG AA contrast for text and controls.
- Do not use `colors.brand.primary` on `colors.surface.card-alt` unless contrast is verified.
- Use state colors only when they reinforce meaning, not as broad theme colors.

## Typography

Typography must follow a clear hierarchy.

- `display-lg` and `display-md` are reserved for major hero areas and marketing panels.
- `headline-lg`, `headline-md`, and `headline-sm` are for page titles, section headers, and dialog titles.
- `body-lg` is for longer descriptive content.
- `body-md` is the default reading size for form labels, helper copy, and general UI text.
- `label-lg` and `label-sm` are for buttons, chips, badges, and compact metadata.

Rules:
- Use `Inter` consistently unless a widget intentionally overrides it for a brand or editorial effect.
- Use bold weights only for titles, CTA text, and selected state labels.
- Keep line heights generous in body text and tighter in headlines.
- Do not mix typography families within a single component unless explicitly specified by the component token.

## Layout (Layout & Spacing)

Spacing uses a consistent 4px-based scale, with 8px as the primary rhythm.

- Use `spacing.2` for tight gaps and icon spacing.
- Use `spacing.4` to `spacing.6` for most form, card, and section spacing.
- Use `spacing.8` and above for page-level separation and major vertical rhythm.

Breakpoint model:

- `mobile`: `< 600px`
- `tablet`: `600px` to `< 900px`
- `laptop`: `900px` to `< 1200px`
- `desktop`: `1200px` to `< 1600px`
- `wide`: `>= 1600px`

Responsive behavior:

- Mobile should prioritize single-column flow and simplified navigation.
- Tablet should support compact split layouts and two-column grids where content allows.
- Laptop should introduce denser multi-column content and persistent side panels.
- Desktop should support full workspace layouts with standard sidebars and wider content areas.
- Wide screens should expand content thoughtfully without letting lines become too long.
- Light and dark themes must use the same semantic token set and only differ in surface, text, and outline values.
- Indented sublayouts, card spacing, and component geometry must remain consistent across both themes.

Layout rules:
- Center major content in constrained containers on large screens.
- Use split layouts for builder and admin workflows when the viewport allows it.
- Prefer responsive stacking over horizontal crowding on small screens.
- Keep dense editor UIs segmented into panels and tabs rather than long scrolling monoliths.

Density rules:
- Auth screens should feel spacious and calm.
- Dashboard and admin screens should feel information-dense but not cramped.
- Form builder screens may be denser, but maintain clear panel boundaries.

## Elevation & Depth

The system is mostly flat, with selective depth.

- `elevation.none` is used for background containers, selected tabs, and full-bleed sections.
- `elevation.sm` is the default for cards and lightweight panels.
- `elevation.md` is for dialogs and stronger floating containers.
- `elevation.lg` and `elevation.xl` are reserved for modal emphasis, hero blocks, and high-priority overlays.

Rules:
- Prefer borders over heavy shadows for most surfaces.
- Use elevation to separate layers, not to create decorative depth everywhere.
- Do not stack multiple elevated surfaces unless the interaction requires a modal hierarchy.
- Keep gradients rare and mostly limited to hero or onboarding surfaces.

## Shapes

Border radii are semantic and consistent.

- `rounded.sm` for buttons, inputs, badges, and compact chips.
- `rounded.md` for list items and moderate cards.
- `rounded.lg` for standard cards and panels.
- `rounded.xl` for hero panels and large dialogs.
- `rounded.full` for pills, status badges, and avatar-like circular accents.

Rules:
- Use the same radius family across a page unless a component has a distinct interaction role.
- Avoid mixing sharp and rounded styles without a functional reason.

## Components

### button-primary

- `backgroundColor`: `{colors.brand.primary}`
- `textColor`: `{colors.surface.card}`
- `padding`: `{spacing.4}` vertical and `{spacing.6}` horizontal
- `rounded`: `{rounded.sm}`
- `typography`: `{typography.label-lg}`
- states:
  - hover: `{colors.brand.primary-strong}`
  - active: `{colors.brand.primary-strong}`
  - disabled: muted background with light text contrast preserved

Use for:
- primary form submission
- save/publish actions
- main navigation confirmations

### button-secondary

- `backgroundColor`: `{colors.surface.card}`
- `textColor`: `{colors.text.primary}`
- `padding`: `{spacing.4}` vertical and `{spacing.6}` horizontal
- `rounded`: `{rounded.sm}`
- `typography`: `{typography.label-lg}`
- states:
  - hover: `{colors.surface.card-alt}`
  - disabled: subdued card background with muted text

Use for:
- cancel actions
- secondary workflows
- low-priority choices

### card

- `backgroundColor`: `{colors.surface.card}`
- `textColor`: `{colors.text.primary}`
- `padding`: `{spacing.6}`
- `rounded`: `{rounded.lg}`
- `typography`: inherited, usually `{typography.body-md}`
- `elevation`: `{elevation.sm}`
- `border`: `{colors.border.strong}`

Use for:
- dashboards
- panels
- summary blocks
- reusable grouped content

### input

- `backgroundColor`: `{colors.surface.card-alt}`
- `textColor`: `{colors.text.primary}`
- `padding`: `{spacing.3}` vertical and `{spacing.4}` horizontal
- `rounded`: `{rounded.sm}`
- `typography`: `{typography.body-md}`
- `border`: `{colors.border.subtle}`
- `focusBorderColor`: `{colors.brand.primary}`
- `placeholderColor`: `{colors.text.subtle}`
- states:
  - focused: brand focus border
  - disabled: muted surface with reduced emphasis

Use for:
- text fields
- dropdown inputs
- search fields
- builder property fields

### list-item

- `backgroundColor`: `{colors.surface.card}`
- `textColor`: `{colors.text.primary}`
- `padding`: `{spacing.4}` vertical and `{spacing.5}` horizontal
- `rounded`: `{rounded.md}`
- `typography`: `{typography.body-md}`
- `border`: `{colors.border.strong}`
- states:
  - hover: `{colors.surface.card-alt}`
  - selected: tinted border or tinted background using `{colors.brand.primary-soft}`

Use for:
- navigation lists
- admin rows
- response rows
- chooser lists

## Do’s and Don’ts

Do:
- Use primary color only for the most important action on a surface.
- Use secondary buttons for reversible or low-priority actions.
- Keep spacing aligned to the spacing scale.
- Preserve WCAG AA contrast for text and controls.
- Use semantic tokens instead of ad hoc hex values in component descriptions.
- Keep components visually consistent across pages and breakpoints.

Don’t:
- Introduce random colors outside the token set.
- Mix radii styles within the same component family.
- Use elevation when a simple border is sufficient.
- Use the primary color for every interactive element.
- Overload the UI with multiple competing accent colors.
- Create page-specific one-off styles that cannot be expressed as tokens.
