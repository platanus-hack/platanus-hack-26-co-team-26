import 'dart:async';
import 'dart:typed_data';

import 'package:nearby_connections/nearby_connections.dart';

import '../core/logging.dart';
import 'transport_adapter.dart';

/// Transporte P0. Nearby Connections negocia solo entre BLE, Wi-Fi Direct y
/// hotspot, así que no implementamos GATT ni fragmentación.
///
/// Requiere Google Play Services. Si falta, `capabilities()` lo reporta y la
/// UI oculta el transporte en vez de fingir que funciona.
class NearbyTransport implements TransportAdapter {
  static const _serviceId = 'us.platanus.sismomesh';
  static const _strategy = Strategy.P2P_CLUSTER;

  final _peers = StreamController<PeerEvent>.broadcast();
  final _inbound = StreamController<InboundFrame>.broadcast();
  final _connected = <String>{};
  final _names = <String, String>{};

  @override
  TransportId get id => TransportId.nearby;
  @override
  Stream<PeerEvent> get peers => _peers.stream;
  @override
  Stream<InboundFrame> get inbound => _inbound.stream;
  @override
  Set<String> get connectedPeers => Set.unmodifiable(_connected);

  @override
  Future<TransportCapabilities> capabilities() async {
    try {
      final ok = await Nearby().checkLocationPermission();
      return TransportCapabilities(
          supported: true, reason: ok ? null : 'faltan permisos de ubicación');
    } catch (e) {
      return TransportCapabilities(supported: false, reason: 'Play Services no disponible: $e');
    }
  }

  @override
  Future<void> start({required String selfName, required String incidentId}) async {
    // En P2P_CLUSTER cada nodo anuncia Y descubre a la vez: cualquiera puede
    // iniciar la conexión. Es lo que permite que los roles sean simétricos.
    await Nearby().startAdvertising(
      selfName, _strategy,
      serviceId: _serviceId,
      onConnectionInitiated: _onInit,
      onConnectionResult: _onResult,
      onDisconnected: _onDisconnected,
    );
    await Nearby().startDiscovery(
      selfName, _strategy,
      serviceId: _serviceId,
      onEndpointFound: (peerId, name, service) {
        _names[peerId] = name;
        _peers.add(PeerEvent(peerId, PeerState.found, name: name));
        log.i('peer encontrado $name ($peerId)');
        Nearby().requestConnection(selfName, peerId,
            onConnectionInitiated: _onInit,
            onConnectionResult: _onResult,
            onDisconnected: _onDisconnected);
      },
      onEndpointLost: (peerId) {
        _peers.add(PeerEvent(peerId ?? '?', PeerState.lost));
      },
    );
    log.i('nearby iniciado como $selfName');
  }

  void _onInit(String peerId, ConnectionInfo info) {
    _names[peerId] = info.endpointName;
    // Sin verificación de token: en un derrumbe no hay nadie comparando
    // códigos. La confianza NO está en el enlace, está en la firma del bundle.
    Nearby().acceptConnection(
      peerId,
      onPayLoadRecieved: _onPayload,   // sic: el typo está en el plugin, no lo "arreglen"
      onPayloadTransferUpdate: (_, __) {},
    );
  }

  void _onResult(String peerId, Status status) {
    if (status == Status.CONNECTED) {
      _connected.add(peerId);
      _peers.add(PeerEvent(peerId, PeerState.connected, name: _names[peerId]));
      log.i('conectado a ${_names[peerId] ?? peerId}');
    } else {
      log.w('conexión con $peerId terminó en $status');
    }
  }

  void _onDisconnected(String peerId) {
    _connected.remove(peerId);
    _peers.add(PeerEvent(peerId, PeerState.disconnected, name: _names[peerId]));
  }

  void _onPayload(String peerId, Payload payload) {
    if (payload.type != PayloadType.BYTES || payload.bytes == null) return;
    _inbound.add(InboundFrame(payload.bytes!,
        fromPeer: _names[peerId] ?? peerId, transport: TransportId.nearby));
  }

  @override
  Future<bool> send(String peerId, Uint8List payload) async {
    try {
      await Nearby().sendBytesPayload(peerId, payload);
      return true;
    } catch (e) {
      log.w('fallo enviando a $peerId: $e');
      return false;
    }
  }

  @override
  Future<void> stop() async {
    await Nearby().stopAdvertising();
    await Nearby().stopDiscovery();
    await Nearby().stopAllEndpoints();
    _connected.clear();
  }
}
