import 'package:flutter/material.dart';
import '../models/widget_model.dart';

class ImageWidget extends StatelessWidget {
  final WidgetModel widget;

  const ImageWidget({
    super.key,
    required this.widget,
  });

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final url = props['image_url'] ?? '';
    final fitStr = props['fit'] ?? 'contain';
    final altText = props['alt_text'] ?? '';
    final linkUrl = props['link_url'] ?? '';
    final radius = (props['border_radius'] as num?)?.toDouble() ?? 0.0;

    final fit = _getFit(fitStr);

    Widget image;
    if (url.isEmpty) {
      image = const Center(
        child: Icon(Icons.image, size: 48, color: Colors.grey),
      );
    } else {
      image = Image.network(
        url,
        fit: fit,
        semanticLabel: altText,
        errorBuilder: (context, error, stackTrace) {
          return const Center(child: Icon(Icons.broken_image, color: Colors.red));
        },
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return const Center(child: CircularProgressIndicator());
        },
      );
    }

    if (radius > 0) {
      image = ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: image,
      );
    }

    if (linkUrl.isNotEmpty) {
      return InkWell(
        onTap: () {
          // In a real app we might open the browser or navigate
        },
        child: image,
      );
    }

    return image;
  }

  BoxFit _getFit(String val) {
    switch (val) {
      case 'cover': return BoxFit.cover;
      case 'fill': return BoxFit.fill;
      case 'none': return BoxFit.none;
      case 'scale_down': return BoxFit.scaleDown;
      default: return BoxFit.contain;
    }
  }
}
