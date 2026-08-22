import 'dart:async';
import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../core/logging.dart';
import '../protocol/bundle.dart';
import '../protocol/crypto.dart';
import 'bundle_store.dart';

class SqfliteBundleStore implements BundleStore {
  late final Database _db;
  final _changes = StreamController<void>.broadcast();

  @override
  Stream<void> get changes => _changes.stream;

  @override
  Future<void> init() async {
    _db = await openDatabase(
      p.join(await getDatabasesPath(), 'sismomesh.db'),
      version: 1,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE bundles (
            bundle_id      TEXT PRIMARY KEY,
            incident_id    TEXT NOT NULL,
            node_pseudonym TEXT NOT NULL,
            priority       INTEGER NOT NULL,
            created_at     TEXT NOT NULL,
            expires_at     TEXT NOT NULL,
            envelope_json  TEXT NOT NULL,
            forwarded_to   TEXT NOT NULL DEFAULT '',
            uploaded       INTEGER NOT NULL DEFAULT 0,
            verified       INTEGER NOT NULL,
            reject_reason  TEXT,
            received_at    TEXT NOT NULL,
            origin         TEXT NOT NULL
          )''');
        await db.execute(
            'CREATE INDEX idx_pending ON bundles(uploaded, priority, expires_at)');
      },
    );
  }

  @override
  Future<PutResult> put(EmergencyBundle b, {required String origin}) async {
    final dup = await _db.query('bundles',
        columns: ['bundle_id'], where: 'bundle_id = ?', whereArgs: [b.bundleId]);
    if (dup.isNotEmpty) {
      log.d('bundle ${b.bundleId} duplicado (via $origin)');
      return PutResult.duplicate;
    }

    final reason = await BundleCrypto.verify(b);
    // Un bundle inválido se guarda marcado, no se descarta en silencio: en el
    // demo hay que poder mostrar que la malla detectó la manipulación.
    await _db.insert('bundles', {
      'bundle_id': b.bundleId,
      'incident_id': b.payload.incidentId,
      'node_pseudonym': b.payload.nodePseudonym,
      'priority': b.payload.priority,
      'created_at': b.payload.createdAt.toUtc().toIso8601String(),
      'expires_at': b.payload.expiresAt.toUtc().toIso8601String(),
      'envelope_json': b.encode(),
      'verified': reason == null ? 1 : 0,
      'reject_reason': reason,
      'received_at': DateTime.now().toUtc().toIso8601String(),
      'origin': origin,
    });
    _changes.add(null);
    log.i('bundle ${b.bundleId} ${reason == null ? "aceptado" : "RECHAZADO: $reason"} '
        '(via $origin, hop=${b.relay.hopCount})');
    return reason == null ? PutResult.accepted : PutResult.rejected;
  }

  @override
  Future<Set<String>> inventoryDigest() async => (await _db.query('bundles',
          columns: ['bundle_id'], where: 'verified = 1'))
      .map((r) => r['bundle_id'] as String)
      .toSet();

  @override
  Future<List<EmergencyBundle>> getMissing(Set<String> peerHas) async {
    final rows = await _db.query('bundles',
        where: 'verified = 1', orderBy: 'priority ASC, created_at ASC');
    return rows
        .where((r) => !peerHas.contains(r['bundle_id'] as String))
        .map((r) => EmergencyBundle.decode(r['envelope_json'] as String))
        .toList();
  }

  @override
  Future<void> markForwarded(String bundleId, String peerId) async {
    final rows = await _db.query('bundles',
        columns: ['forwarded_to'], where: 'bundle_id = ?', whereArgs: [bundleId]);
    if (rows.isEmpty) return;
    final set = (rows.first['forwarded_to'] as String).split(',').toSet()..add(peerId);
    await _db.update('bundles', {'forwarded_to': set.where((s) => s.isNotEmpty).join(',')},
        where: 'bundle_id = ?', whereArgs: [bundleId]);
  }

  @override
  Future<void> markUploaded(Iterable<String> ids) async {
    if (ids.isEmpty) return;
    final q = List.filled(ids.length, '?').join(',');
    await _db.rawUpdate(
        'UPDATE bundles SET uploaded = 1 WHERE bundle_id IN ($q)', ids.toList());
    _changes.add(null);
  }

  @override
  Future<List<StoredBundle>> pendingUpload({int limit = 50}) => _select(
      where: 'uploaded = 0 AND verified = 1',
      orderBy: 'priority ASC, created_at ASC',
      limit: limit);

  @override
  Future<List<StoredBundle>> all({int limit = 200}) =>
      _select(orderBy: 'received_at DESC', limit: limit);

  Future<List<StoredBundle>> _select(
      {String? where, required String orderBy, required int limit}) async {
    final rows = await _db.query('bundles', where: where, orderBy: orderBy, limit: limit);
    return rows.map((r) => StoredBundle(
          bundle: EmergencyBundle.decode(r['envelope_json'] as String),
          receivedAt: DateTime.parse(r['received_at'] as String),
          forwardedTo: (r['forwarded_to'] as String).split(',').where((s) => s.isNotEmpty).toSet(),
          uploaded: r['uploaded'] == 1,
          verified: r['verified'] == 1,
          rejectReason: r['reject_reason'] as String?,
        )).toList();
  }

  @override
  Future<int> expire(DateTime now) async {
    // Se MARCA, no se borra: un borrado silencioso es indepurable en vivo.
    final n = await _db.rawUpdate(
        "UPDATE bundles SET reject_reason = 'ttl vencido', verified = 0 "
        "WHERE expires_at < ? AND verified = 1",
        [now.toUtc().toIso8601String()]);
    if (n > 0) {
      log.i('$n bundle(s) vencidos por TTL');
      _changes.add(null);
    }
    return n;
  }

  @override
  Future<void> clear() async {
    await _db.delete('bundles');
    _changes.add(null);
  }
}
