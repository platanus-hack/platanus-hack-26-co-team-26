import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import 'bundle.dart';
import 'canonical_json.dart';

/// Identidad criptográfica del nodo.
///
/// El seed vive en almacenamiento cifrado (EncryptedSharedPreferences en
/// Android), no en SharedPreferences plano: la clave privada firma reportes de
/// emergencia y no debe salir en un backup de la app.
class NodeIdentity {
  NodeIdentity._(this._keyPair, this.publicKeyBytes, this.pseudonym);

  static const _algo = Ed25519();
  static const _slot = 'sismomesh.node.seed.v1';
  static const _storage = FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true));

  final SimpleKeyPair _keyPair;
  final Uint8List publicKeyBytes;

  /// base64url de los primeros 12 bytes de SHA-256(pubkey). Sin PII.
  final String pseudonym;

  String get publicKeyB64 => base64.encode(publicKeyBytes);

  static Future<NodeIdentity> load() async {
    var seedB64 = await _storage.read(key: _slot);
    if (seedB64 == null) {
      final rnd = Random.secure();
      final seed = Uint8List.fromList(List.generate(32, (_) => rnd.nextInt(256)));
      seedB64 = base64.encode(seed);
      await _storage.write(key: _slot, value: seedB64);
    }
    final kp = await _algo.newKeyPairFromSeed(base64.decode(seedB64));
    final pub = Uint8List.fromList((await kp.extractPublicKey()).bytes);
    return NodeIdentity._(kp, pub, await pseudonymOf(pub));
  }

  static Future<String> pseudonymOf(List<int> pubkey) async {
    final h = await Sha256().hash(pubkey);
    return base64Url.encode(h.bytes.sublist(0, 12)).replaceAll('=', '');
  }

  Future<Uint8List> sign(List<int> bytes) async =>
      Uint8List.fromList((await _algo.sign(bytes, keyPair: _keyPair)).bytes);
}

class BundleCrypto {
  static const _algo = Ed25519();
  static const _uuid = Uuid();

  /// Construye y firma un bundle. Es el ÚNICO lugar donde se generan los bytes
  /// canónicos del payload; a partir de aquí sólo se propagan.
  static Future<EmergencyBundle> build(
      EmergencyPayload payload, NodeIdentity id) async {
    final bytes = canonicalBytes(payload.toJson());
    final hash = await Sha256().hash(bytes);
    return EmergencyBundle(
      bundleId: _uuid.v4(),
      payloadBytes: bytes,
      payload: payload,
      payloadHash: _hex(hash.bytes),
      signerKeyId: id.pseudonym,
      signerPubkeyB64: id.publicKeyB64,
      signature: base64.encode(await id.sign(bytes)),
    );
  }

  /// Verifica sobre los bytes RECIBIDOS. Devuelve null si es válido, o el
  /// motivo de rechazo. El bundle es auto-verificable: trae su clave pública
  /// y el signer_key_id debe ser el hash de esa clave.
  static Future<String?> verify(EmergencyBundle b) async {
    final pub = base64.decode(b.signerPubkeyB64);
    if (await NodeIdentity.pseudonymOf(pub) != b.signerKeyId) {
      return 'signer_key_id no corresponde a signer_pubkey_b64';
    }
    if (_hex((await Sha256().hash(b.payloadBytes)).bytes) != b.payloadHash) {
      return 'payload_hash no coincide';
    }
    final ok = await _algo.verify(
      b.payloadBytes,
      signature: Signature(base64.decode(b.signature),
          publicKey: SimplePublicKey(pub, type: KeyPairType.ed25519)),
    );
    return ok ? null : 'firma invalida';
  }

  static String _hex(List<int> b) =>
      b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
}
