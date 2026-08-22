import 'dart:async';

import 'package:battery_plus/battery_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

import '../core/logging.dart';
import '../gateway/gateway_sync.dart';
import '../protocol/bundle.dart';
import '../protocol/crypto.dart';
import '../protocol/status.dart';
import '../store/bundle_store.dart';
import '../store/dtn_engine.dart';
import '../store/sqflite_bundle_store.dart';
import '../transport/nearby_transport.dart';
import '../transport/transport_adapter.dart';
import 'node_role.dart';

const kAppVersion = '0.1.0';
const kDefaultIncident = 'demo-bogota-01';

/// Estado central de la app. Un solo objeto observable: con 5 horas y 5 devs,
/// un árbol de providers finamente granulado cuesta más de lo que rinde.
class MeshController extends ChangeNotifier {
  MeshController({this.gatewayUrl = 'http://10.0.2.2:8000'});

  final String gatewayUrl;

  late final NodeIdentity identity;
  late final BundleStore store = SqfliteBundleStore();
  late final TransportAdapter transport = NearbyTransport();
  DtnEngine? _dtn;
  GatewaySync? _gateway;

  NodeRole role = NodeRole.victim;
  String incidentId = kDefaultIncident;
  NodeStatus status = NodeStatus.unconfirmed;
  bool emergencyActive = false;
  int seq = 0;

  TransportCapabilities? transportCaps;
  final peers = <String, PeerEvent>{};
  List<StoredBundle> bundles = const [];

  int get forwarded => _dtn?.forwarded ?? 0;
  int get receivedCount => _dtn?.received ?? 0;
  int get uploaded => _gateway?.uploaded ?? 0;
  String? get uploadError => _gateway?.lastError;

  Future<void> init() async {
    identity = await NodeIdentity.load();
    await store.init();
    store.changes.listen((_) => refresh());
    transportCaps = await transport.capabilities();
    log.i('nodo ${identity.pseudonym} listo · transporte '
        '${transportCaps!.supported ? "disponible" : "NO: ${transportCaps!.reason}"}');
    await refresh();
  }

  Future<void> refresh() async {
    bundles = await store.all();
    notifyListeners();
  }

  /// Activación manual del incidente. No espera a ningún feed oficial: el
  /// playbook lo declara explícitamente como camino P0.
  Future<void> activateEmergency(NodeStatus s) async {
    status = s;
    if (!emergencyActive) {
      emergencyActive = true;
      await transport.start(selfName: identity.pseudonym, incidentId: incidentId);
      transport.peers.listen((e) {
        peers[e.peerId] = e;
        notifyListeners();
      });
      _dtn = DtnEngine(store: store, transport: transport)..start();
      if (role == NodeRole.gateway) {
        _gateway = GatewaySync(store: store, baseUrl: gatewayUrl)..start();
      }
    }
    await emitReport();
    notifyListeners();
  }

  /// Genera, firma y guarda un reporte propio. Se guarda en el store local
  /// primero: el envío es consecuencia del store, no al revés. Por eso
  /// funciona sin nadie cerca.
  Future<void> emitReport() async {
    final payload = EmergencyPayload(
      incidentId: incidentId,
      nodePseudonym: identity.pseudonym,
      seq: ++seq,
      createdAt: DateTime.now().toUtc(),
      ttlS: 86400,
      priority: switch (status) {
        NodeStatus.trapped || NodeStatus.help => 0,
        _ => 1,
      },
      status: status,
      userReported: true,
      location: await _location(),
      // evidence queda vacío en el núcleo: los campos existen, los llena D4.
      evidence: const Evidence(),
      device: DeviceInfo(
        batteryPct: await _battery(),
        capabilities: Capabilities(
          nearby: transportCaps?.supported ?? false,
          camera: true,
          gnss: true,
        ),
        appVersion: kAppVersion,
      ),
    );
    final bundle = await BundleCrypto.build(payload, identity);
    await store.put(bundle, origin: 'self');
  }

  Future<GeoPoint?> _location() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      final p = await Geolocator.getCurrentPosition(
          timeLimit: const Duration(seconds: 6));
      return GeoPoint(lat: p.latitude, lon: p.longitude, accuracyM: p.accuracy,
          source: 'gnss', measuredAt: p.timestamp.toUtc());
    } catch (e) {
      log.w('sin ubicación: $e');
      return null;   // null = no medido. Jamás una coordenada inventada.
    }
  }

  Future<int?> _battery() async {
    try {
      return await Battery().batteryLevel;
    } catch (_) {
      return null;
    }
  }

  Future<void> setRole(NodeRole r) async {
    role = r;
    if (r == NodeRole.gateway && emergencyActive && _gateway == null) {
      _gateway = GatewaySync(store: store, baseUrl: gatewayUrl)..start();
    }
    notifyListeners();
  }

  Future<void> resetDemo() async {
    await store.clear();
    seq = 0;
    log.clear();
    await refresh();
  }

  @override
  void dispose() {
    _dtn?.stop();
    _gateway?.stop();
    transport.stop();
    super.dispose();
  }
}
