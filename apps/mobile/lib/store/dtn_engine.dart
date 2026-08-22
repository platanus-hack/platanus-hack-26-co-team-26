import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import '../core/logging.dart';
import '../protocol/bundle.dart';
import '../transport/transport_adapter.dart';
import 'bundle_store.dart';

/// Motor store-carry-forward.
///
/// Ciclo por contacto: peer conectado -> intercambio de inventario -> se envía
/// lo que al otro le falta -> se marca reenviado. No hay ruta extremo a
/// extremo: hay encuentros oportunistas.
class DtnEngine {
  DtnEngine({required this.store, required this.transport});

  final BundleStore store;
  final TransportAdapter transport;

  final _subs = <StreamSubscription>[];
  Timer? _ttlTimer, _gossipTimer;
  int forwarded = 0, received = 0;

  Future<void> start() async {
    _subs.add(transport.inbound.listen(_onInbound));
    _subs.add(transport.peers.listen((e) {
      if (e.state == PeerState.connected) _syncWith(e.peerId);
    }));

    // Reintento periódico: un peer puede conectarse mientras el store está
    // vacío y quedar sin nada que sincronizar hasta el siguiente encuentro.
    _gossipTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      for (final p in transport.connectedPeers) {
        _syncWith(p);
      }
    });
    _ttlTimer = Timer.periodic(const Duration(seconds: 60),
        (_) => store.expire(DateTime.now()));
    log.i('motor DTN iniciado');
  }

  /// Tipos de trama. Prefijo de 1 byte sobre el mismo canal de bytes.
  static const _frameInventory = 0x01;
  static const _frameBundle = 0x02;

  Future<void> _onInbound(InboundFrame f) async {
    if (f.bytes.isEmpty) return;
    final body = utf8.decode(f.bytes.sublist(1), allowMalformed: true);
    try {
      switch (f.bytes.first) {
        case _frameInventory:
          final have = ((jsonDecode(body) as Map)['have'] as List).cast<String>();
          await onInventory(f.fromPeer, have.toSet());
        case _frameBundle:
          received++;
          final b = EmergencyBundle.decode(body);
          // La capa de relay se añade ANTES de guardar, sin tocar el payload
          // firmado: por eso la firma del emisor original sobrevive N saltos.
          await store.put(
              b.withRelay(b.relay.hop(
                  from: f.fromPeer, transport: f.transport.name, rssi: f.rssi)),
              origin: f.fromPeer);
        default:
          log.w('trama desconocida 0x${f.bytes.first.toRadixString(16)} de ${f.fromPeer}');
      }
    } catch (e) {
      log.w('trama ilegible de ${f.fromPeer}: $e');
    }
  }

  /// Anuncia a un peer qué bundles ya tenemos, para que nos mande sólo lo que
  /// nos falta. Con 3 teléfonos el inventario es una lista plana.
  Future<void> _syncWith(String peerId) async {
    final digest = await store.inventoryDigest();
    final msg = utf8.encode(jsonEncode({'have': digest.toList()}));
    await transport.send(peerId, Uint8List.fromList([_frameInventory, ...msg]));
  }

  Future<void> onInventory(String peerId, Set<String> peerHas) async {
    final missing = await store.getMissing(peerHas);
    if (missing.isEmpty) return;
    log.i('enviando ${missing.length} bundle(s) a $peerId');
    for (final b in missing) {
      final bytes = Uint8List.fromList([_frameBundle, ...utf8.encode(b.encode())]);
      if (await transport.send(peerId, bytes)) {
        await store.markForwarded(b.bundleId, peerId);
        forwarded++;
      }
    }
  }

  Future<void> stop() async {
    _ttlTimer?.cancel();
    _gossipTimer?.cancel();
    for (final s in _subs) {
      await s.cancel();
    }
    _subs.clear();
  }
}
