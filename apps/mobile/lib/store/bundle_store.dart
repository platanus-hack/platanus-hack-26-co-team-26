import '../protocol/bundle.dart';

enum PutResult { accepted, duplicate, rejected, expired }

class StoredBundle {
  StoredBundle({required this.bundle, required this.receivedAt,
      required this.forwardedTo, required this.uploaded, required this.verified,
      this.rejectReason});

  final EmergencyBundle bundle;
  final DateTime receivedAt;
  final Set<String> forwardedTo;   // peers a los que ya se envió: evita re-enviar en bucle
  final bool uploaded, verified;
  final String? rejectReason;
}

/// Almacén persistente. Sobrevive al cierre de la app: es el requisito que
/// convierte "mensajería" en "store-carry-forward".
abstract interface class BundleStore {
  Future<void> init();
  Future<PutResult> put(EmergencyBundle b, {required String origin});

  /// IDs que este nodo tiene y el peer no. En el núcleo el inventario es una
  /// lista plana: con 3 teléfonos un Bloom filter resuelve un problema que no
  /// tenemos. La firma queda lista para cambiarlo sin refactor.
  Future<List<EmergencyBundle>> getMissing(Set<String> peerHas);
  Future<Set<String>> inventoryDigest();

  Future<void> markForwarded(String bundleId, String peerId);
  Future<void> markUploaded(Iterable<String> bundleIds);
  Future<List<StoredBundle>> pendingUpload({int limit = 50});
  Future<List<StoredBundle>> all({int limit = 200});
  Future<int> expire(DateTime now);
  Future<void> clear();
  Stream<void> get changes;
}
