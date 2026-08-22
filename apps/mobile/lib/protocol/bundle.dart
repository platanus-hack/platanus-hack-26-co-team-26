import 'dart:convert';
import 'dart:typed_data';

import 'canonical_json.dart';
import 'status.dart';

/// Procedencia de cada dato. Ver README §C.0 y docs/CORE-5H.md §6.
enum Provenance { measured, derived, assumed, reference, imputed }

/// Capacidades reales del teléfono, medidas en runtime.
/// Cumple el gate del playbook: no soportado != éxito simulado.
class Capabilities {
  const Capabilities({
    this.nearby = false,
    this.bleGatt = false,
    this.wifiAware = false,
    this.uwb = false,
    this.camera = false,
    this.gnss = false,
  });

  final bool nearby, bleGatt, wifiAware, uwb, camera, gnss;

  Map<String, dynamic> toJson() => {
        'nearby': nearby, 'ble_gatt': bleGatt, 'wifi_aware': wifiAware,
        'uwb': uwb, 'camera': camera, 'gnss': gnss,
      };

  static Capabilities fromJson(Map<String, dynamic>? j) => j == null
      ? const Capabilities()
      : Capabilities(
          nearby: j['nearby'] == true, bleGatt: j['ble_gatt'] == true,
          wifiAware: j['wifi_aware'] == true, uwb: j['uwb'] == true,
          camera: j['camera'] == true, gnss: j['gnss'] == true);
}

class GeoPoint {
  const GeoPoint({required this.lat, required this.lon, this.accuracyM,
      required this.source, required this.measuredAt});

  final double lat, lon;
  final double? accuracyM;
  final String source;              // gnss | network | peerDerived | manual
  final DateTime measuredAt;        // separado de createdAt: puede estar vieja

  Map<String, dynamic> toJson() => {
        'lat': lat, 'lon': lon, 'accuracy_m': accuracyM,
        'source': source, 'measured_at': measuredAt.toUtc().toIso8601String(),
      };

  static GeoPoint? fromJson(Map<String, dynamic>? j) => j == null
      ? null
      : GeoPoint(lat: (j['lat'] as num).toDouble(), lon: (j['lon'] as num).toDouble(),
          accuracyM: (j['accuracy_m'] as num?)?.toDouble(),
          source: j['source'] as String? ?? 'unknown',
          measuredAt: DateTime.parse(j['measured_at'] as String));
}

/// Evidencia. En el núcleo de 5 h `motion` y `ppg` viajan en null y `peers`
/// vacío: el campo ya existe, falta la implementación que lo llena (D4).
///
/// null significa NO MEDIDO. Nunca cero, nunca un valor por defecto.
class Evidence {
  const Evidence({this.motion, this.ppg, this.peers = const []});

  final Map<String, dynamic>? motion;   // {detected, pattern, confidence, window_s, provenance, observed_at}
  final Map<String, dynamic>? ppg;      // {hr_bpm, sqi, waveform_ref, provenance, measured_at}
  final List<Map<String, dynamic>> peers;

  bool get isEmpty => motion == null && ppg == null && peers.isEmpty;

  Map<String, dynamic> toJson() => {'motion': motion, 'ppg': ppg, 'peers': peers};

  static Evidence fromJson(Map<String, dynamic>? j) => j == null
      ? const Evidence()
      : Evidence(
          motion: (j['motion'] as Map?)?.cast<String, dynamic>(),
          ppg: (j['ppg'] as Map?)?.cast<String, dynamic>(),
          peers: ((j['peers'] as List?) ?? const [])
              .map((e) => (e as Map).cast<String, dynamic>()).toList());
}

class DeviceInfo {
  const DeviceInfo({this.batteryPct, required this.capabilities, required this.appVersion});

  final int? batteryPct;
  final Capabilities capabilities;
  final String appVersion;

  Map<String, dynamic> toJson() => {
        'battery_pct': batteryPct,
        'capabilities': capabilities.toJson(),
        'app_version': appVersion,
      };

  static DeviceInfo fromJson(Map<String, dynamic>? j) => DeviceInfo(
        batteryPct: (j?['battery_pct'] as num?)?.toInt(),
        capabilities: Capabilities.fromJson((j?['capabilities'] as Map?)?.cast<String, dynamic>()),
        appVersion: j?['app_version'] as String? ?? 'unknown',
      );
}

/// Contenido firmado del bundle. Es inmutable desde que sale del nodo emisor.
class EmergencyPayload {
  const EmergencyPayload({
    required this.incidentId, required this.nodePseudonym, required this.seq,
    required this.createdAt, required this.ttlS, required this.priority,
    required this.status, required this.userReported,
    this.location, this.evidence = const Evidence(), required this.device,
  });

  final String incidentId, nodePseudonym;
  final int seq, ttlS, priority;
  final DateTime createdAt;
  final NodeStatus status;
  final bool userReported;
  final GeoPoint? location;
  final Evidence evidence;
  final DeviceInfo device;

  DateTime get expiresAt => createdAt.add(Duration(seconds: ttlS));
  bool isExpired(DateTime now) => now.isAfter(expiresAt);

  Map<String, dynamic> toJson() => {
        'incident_id': incidentId,
        'node_pseudonym': nodePseudonym,
        'seq': seq,
        'created_at': createdAt.toUtc().toIso8601String(),
        'ttl_s': ttlS,
        'priority': priority,
        'status': status.wire,
        'user_reported': userReported,
        'location': location?.toJson(),
        'evidence': evidence.toJson(),
        'device': device.toJson(),
      };

  static EmergencyPayload fromJson(Map<String, dynamic> j) => EmergencyPayload(
        incidentId: j['incident_id'] as String,
        nodePseudonym: j['node_pseudonym'] as String,
        seq: (j['seq'] as num).toInt(),
        createdAt: DateTime.parse(j['created_at'] as String),
        ttlS: (j['ttl_s'] as num).toInt(),
        priority: (j['priority'] as num).toInt(),
        status: NodeStatus.parse(j['status'] as String?),
        userReported: j['user_reported'] == true,
        location: GeoPoint.fromJson((j['location'] as Map?)?.cast<String, dynamic>()),
        evidence: Evidence.fromJson((j['evidence'] as Map?)?.cast<String, dynamic>()),
        device: DeviceInfo.fromJson((j['device'] as Map?)?.cast<String, dynamic>()),
      );
}

/// Metadata de relay: MUTABLE y fuera de la firma.
/// Cada salto añade su capa sin invalidar la del emisor original.
class RelayMeta {
  const RelayMeta({this.hopCount = 0, this.receivedFrom, this.transport,
      this.rssi, this.gatewayPosition});

  final int hopCount;
  final String? receivedFrom, transport;
  final int? rssi;
  final Map<String, dynamic>? gatewayPosition;

  RelayMeta hop({required String from, required String transport, int? rssi}) =>
      RelayMeta(hopCount: hopCount + 1, receivedFrom: from,
          transport: transport, rssi: rssi, gatewayPosition: gatewayPosition);

  Map<String, dynamic> toJson() => {
        'hop_count': hopCount, 'received_from': receivedFrom,
        'transport': transport, 'rssi': rssi, 'gateway_position': gatewayPosition,
      };

  static RelayMeta fromJson(Map<String, dynamic>? j) => j == null
      ? const RelayMeta()
      : RelayMeta(
          hopCount: (j['hop_count'] as num?)?.toInt() ?? 0,
          receivedFrom: j['received_from'] as String?,
          transport: j['transport'] as String?,
          rssi: (j['rssi'] as num?)?.toInt(),
          gatewayPosition: (j['gateway_position'] as Map?)?.cast<String, dynamic>());
}

/// Sobre completo: lo que viaja por el cable.
///
/// INVARIANTE CENTRAL: [payloadBytes] es la fuente de verdad. Nunca se
/// re-serializa el payload al reenviar ni al verificar; se propagan los bytes
/// exactos que llegaron. Ese detalle es lo que hace que la firma sobreviva
/// N saltos y cruce el límite Dart/Python sin romperse.
class EmergencyBundle {
  const EmergencyBundle({
    required this.bundleId, required this.payloadBytes, required this.payload,
    required this.payloadHash, required this.signerKeyId,
    required this.signerPubkeyB64, required this.signature,
    this.relay = const RelayMeta(), this.version = 1,
  });

  final int version;
  final String bundleId;
  final Uint8List payloadBytes;      // <- fuente de verdad, no se regenera
  final EmergencyPayload payload;    // <- vista parseada, solo lectura
  final String payloadHash, signerKeyId, signerPubkeyB64, signature;
  final RelayMeta relay;

  EmergencyBundle withRelay(RelayMeta r) => EmergencyBundle(
        bundleId: bundleId, payloadBytes: payloadBytes, payload: payload,
        payloadHash: payloadHash, signerKeyId: signerKeyId,
        signerPubkeyB64: signerPubkeyB64, signature: signature,
        relay: r, version: version,
      );

  Map<String, dynamic> toWire() => {
        'v': version,
        'bundle_id': bundleId,
        'payload_b64': base64.encode(payloadBytes),   // bytes originales, intactos
        'payload_hash': payloadHash,
        'signer_key_id': signerKeyId,
        'signer_pubkey_b64': signerPubkeyB64,
        'signature': signature,
        'relay': relay.toJson(),
      };

  String encode() => jsonEncode(toWire());

  static EmergencyBundle fromWire(Map<String, dynamic> j) {
    final bytes = base64.decode(j['payload_b64'] as String);
    return EmergencyBundle(
      version: (j['v'] as num?)?.toInt() ?? 1,
      bundleId: j['bundle_id'] as String,
      payloadBytes: Uint8List.fromList(bytes),
      payload: EmergencyPayload.fromJson(
          (jsonDecode(utf8.decode(bytes)) as Map).cast<String, dynamic>()),
      payloadHash: j['payload_hash'] as String,
      signerKeyId: j['signer_key_id'] as String,
      signerPubkeyB64: j['signer_pubkey_b64'] as String,
      signature: j['signature'] as String,
      relay: RelayMeta.fromJson((j['relay'] as Map?)?.cast<String, dynamic>()),
    );
  }

  static EmergencyBundle decode(String s) =>
      fromWire((jsonDecode(s) as Map).cast<String, dynamic>());
}
