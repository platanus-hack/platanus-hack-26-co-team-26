import 'dart:collection';

import 'package:flutter/foundation.dart';

enum LogLevel { d, i, w, e }

class LogLine {
  LogLine(this.level, this.message) : at = DateTime.now();
  final LogLevel level;
  final String message;
  final DateTime at;
}

/// Log en memoria con espejo en consola.
///
/// Regla del playbook: todo log lleva bundle_id. Con tres teléfonos sobre la
/// mesa, un bug que no se puede rastrear por bundle_id no se puede depurar.
class _Log {
  static const _max = 500;
  final ring = ListQueue<LogLine>();
  final listeners = <VoidCallback>[];

  void _add(LogLevel l, String m) {
    if (ring.length >= _max) ring.removeFirst();
    ring.addLast(LogLine(l, m));
    if (kDebugMode) debugPrint('[${l.name}] $m');
    for (final f in listeners) {
      f();
    }
  }

  void d(String m) => _add(LogLevel.d, m);
  void i(String m) => _add(LogLevel.i, m);
  void w(String m) => _add(LogLevel.w, m);
  void e(String m) => _add(LogLevel.e, m);
  void clear() => ring.clear();
}

final log = _Log();
