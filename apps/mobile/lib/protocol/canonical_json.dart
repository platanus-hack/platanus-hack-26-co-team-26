import 'dart:convert';
import 'dart:typed_data';

/// JSON canónico: claves ordenadas recursivamente, separadores compactos, UTF-8.
///
/// Estos son los bytes que se firman. Los produce SOLO el nodo emisor.
/// Nadie los vuelve a generar: se transmiten en base64 y se verifican tal como
/// llegan. Por eso una diferencia de formato entre Dart y Python es inocua.
Uint8List canonicalBytes(Map<String, dynamic> obj) =>
    Uint8List.fromList(utf8.encode(jsonEncode(_sort(obj))));

dynamic _sort(dynamic v) {
  if (v is Map) {
    final keys = v.keys.map((k) => k as String).toList()..sort();
    return {for (final k in keys) k: _sort(v[k])};
  }
  if (v is List) return v.map(_sort).toList();
  return v;
}
