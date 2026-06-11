// css_injector_web.dart
import 'dart:html' as html;

String scopeCss(String css, String selector) {
  final RegExp regExp = RegExp(r'([^\r\n,{}]+)(?=\s*\{)');
  return css.replaceAllMapped(regExp, (match) {
    final sel = match.group(1)!.trim();
    if (sel.startsWith('@') || sel.startsWith('from') || sel.startsWith('to') || sel.contains('%')) {
      return sel;
    }
    // Handle multiple selectors separated by commas
    return sel.split(',').map((s) => '$selector ${s.trim()}').join(', ');
  });
}

void injectCss(String css) {
  final scoped = scopeCss(css, '[flt-value-key="form-canvas-root"]');
  final existing = html.document.getElementById('custom-form-styles');
  if (existing != null) {
    existing.text = scoped;
  } else {
    final styleElement = html.StyleElement()
      ..id = 'custom-form-styles'
      ..text = scoped;
    html.document.head?.append(styleElement);
  }
}
