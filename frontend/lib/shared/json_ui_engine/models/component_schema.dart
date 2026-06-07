import 'visibility_rule.dart';

class PrimitiveRef {
  final String primitive;
  final String propertyKey;
  final String? labelFromProperty;
  final VisibilityRules? visibility;
  final Map<String, dynamic> staticProperties;

  const PrimitiveRef({
    required this.primitive,
    required this.propertyKey,
    this.labelFromProperty,
    this.visibility,
    required this.staticProperties,
  });

  factory PrimitiveRef.fromJson(Map<String, dynamic> json) {
    return PrimitiveRef(
      primitive: json['primitive'] ?? '',
      propertyKey: json['property_key'] ?? json['propertyKey'] ?? '',
      labelFromProperty: json['label_from_property'] ?? json['labelFromProperty'],
      visibility: json['visibility'] != null ? VisibilityRules.fromJson(json['visibility']) : null,
      staticProperties: Map<String, dynamic>.from(json['static_properties'] ?? json['staticProperties'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'primitive': primitive,
      'property_key': propertyKey,
      'label_from_property': labelFromProperty,
      'visibility': visibility?.toJson(),
      'static_properties': staticProperties,
    };
  }
}

class PropertyDef {
  final String key;
  final String type;
  final dynamic defaultValue;
  final bool required;

  const PropertyDef({
    required this.key,
    required this.type,
    this.defaultValue,
    required this.required,
  });

  factory PropertyDef.fromJson(Map<String, dynamic> json) {
    return PropertyDef(
      key: json['key'] ?? '',
      type: json['type'] ?? 'string',
      defaultValue: json['default'] ?? json['defaultValue'],
      required: json['required'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'key': key,
      'type': type,
      'default': defaultValue,
      'required': required,
    };
  }
}

class ComponentSchema {
  final String type;
  final String displayName;
  final String concept;
  final List<PrimitiveRef> composition;
  final List<PropertyDef> properties;
  final bool offlineSupport;
  final Map<String, dynamic> previewSchema;

  const ComponentSchema({
    required this.type,
    required this.displayName,
    required this.concept,
    required this.composition,
    required this.properties,
    required this.offlineSupport,
    required this.previewSchema,
  });

  factory ComponentSchema.fromJson(Map<String, dynamic> json) {
    return ComponentSchema(
      type: json['type'] ?? '',
      displayName: json['display_name'] ?? json['displayName'] ?? '',
      concept: json['concept'] ?? 'form_field',
      composition: (json['composition'] as List?)
              ?.map((c) => PrimitiveRef.fromJson(c as Map<String, dynamic>))
              .toList() ??
          const [],
      properties: (json['properties'] as List?)
              ?.map((p) => PropertyDef.fromJson(p as Map<String, dynamic>))
              .toList() ??
          const [],
      offlineSupport: json['offline_support'] ?? json['offlineSupport'] ?? true,
      previewSchema: Map<String, dynamic>.from(json['preview_schema'] ?? json['previewSchema'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'display_name': displayName,
      'concept': concept,
      'composition': composition.map((c) => c.toJson()).toList(),
      'properties': properties.map((p) => p.toJson()).toList(),
      'offline_support': offlineSupport,
      'preview_schema': previewSchema,
    };
  }
}
