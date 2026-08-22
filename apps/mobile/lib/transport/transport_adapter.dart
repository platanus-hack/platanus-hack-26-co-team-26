import 'dart:typed_data';

enum TransportId { nearby, bleGatt, acoustic }

enum PeerState { found, lost, connected, disconnected }

class PeerEvent {
  const PeerEvent(this.peerId, this.state, {this.name, this.rssi});
  final String peerId;
  final PeerState state;
  final String? name;
  final int? rssi;
}

/// Trama cruda recibida. El transporte NO interpreta el contenido: sólo mueve
/// bytes. Quién es inventario y quién es bundle lo decide el motor DTN.
class InboundFrame {
  const InboundFrame(this.bytes, {required this.fromPeer,
      required this.transport, this.rssi});
  final Uint8List bytes;
  final String fromPeer;
  final TransportId transport;
  final int? rssi;
}

class TransportCapabilities {
  const TransportCapabilities({required this.supported, this.reason});
  final bool supported;
  final String? reason;    // por qué NO se soporta: se muestra, no se oculta
}

/// Un transporte concreto. La app nunca habla con Nearby ni con BLE
/// directamente: sólo con esta interfaz.
abstract interface class TransportAdapter {
  TransportId get id;
  Future<TransportCapabilities> capabilities();
  Future<void> start({required String selfName, required String incidentId});
  Future<void> stop();
  Stream<PeerEvent> get peers;
  Stream<InboundFrame> get inbound;
  Future<bool> send(String peerId, Uint8List payload);
  Set<String> get connectedPeers;
}
