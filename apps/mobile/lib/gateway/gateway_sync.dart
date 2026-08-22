import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../core/logging.dart';
import '../store/bundle_store.dart';

/// Subida al backend desde el nodo gateway.
///
/// La cola es el store: si no hay red, los bundles simplemente siguen sin
/// marcar como subidos. Cuando vuelve la conectividad se drenan solos.
class GatewaySync {
  GatewaySync({required this.store, required this.baseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 5),
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ));

  final BundleStore store;
  final String baseUrl;
  final Dio _dio;
  static const _uuid = Uuid();

  Timer? _timer;
  bool _busy = false;
  int uploaded = 0, failures = 0;
  String? lastError;

  void start({Duration every = const Duration(seconds: 5)}) {
    _timer = Timer.periodic(every, (_) => drain());
    Connectivity().onConnectivityChanged.listen((_) => drain());
    log.i('gateway sync -> $baseUrl');
  }

  Future<void> drain() async {
    if (_busy) return;
    _busy = true;
    try {
      final pending = await store.pendingUpload(limit: 50);
      if (pending.isEmpty) return;

      // Idempotency-Key estable por lote: reintentar tras un timeout no
      // duplica nada del lado del servidor.
      final key = _uuid.v4();
      final res = await _dio.post<Map<String, dynamic>>(
        '/bundles/batch',
        data: {'bundles': pending.map((s) => s.bundle.toWire()).toList()},
        options: Options(headers: {'Idempotency-Key': key}),
      );
      await store.markUploaded(pending.map((s) => s.bundle.bundleId));
      uploaded += pending.length;
      lastError = null;
      log.i('subidos ${pending.length}: ${jsonEncode(res.data)}');
    } on DioException catch (e) {
      failures++;
      lastError = e.message;
      log.w('subida falló (quedan en cola): ${e.message}');
    } finally {
      _busy = false;
    }
  }

  void stop() => _timer?.cancel();
}
