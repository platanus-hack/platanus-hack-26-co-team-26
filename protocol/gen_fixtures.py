#!/usr/bin/env python3
"""Genera los fixtures canonicos de EmergencyBundle v1.

Fuente de verdad del contrato. Cualquier cambio aqui obliga a regenerar
fixtures/ y a avisar a los consumidores (app Flutter, backend, dashboard).

Uso:  python3 protocol/gen_fixtures.py
"""
import base64, hashlib, json, os, sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

OUT = os.path.join(os.path.dirname(__file__), "..", "fixtures")
INCIDENT = "demo-bogota-01"

# Clave DETERMINISTA: solo para fixtures y tests. Jamas en produccion.
SEED = bytes(range(32))


def canonical(obj) -> bytes:
    """JSON canonico: claves ordenadas, separadores compactos, UTF-8.

    Estos son los bytes que se firman. Nadie los re-serializa nunca:
    se transmiten en base64 y se verifican tal cual llegan.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def pseudonym(pub_raw: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(pub_raw).digest()[:12]).decode().rstrip("=")


def payload(seq, status, *, created, ttl_s=86400, priority=0,
            loc=None, evidence=None, battery=78, node=None):
    return {
        "incident_id": INCIDENT,
        "node_pseudonym": node,
        "seq": seq,
        "created_at": created,
        "ttl_s": ttl_s,
        "priority": priority,
        "status": status,
        "user_reported": True,
        "location": loc,
        "evidence": evidence or {"motion": None, "ppg": None, "peers": []},
        "device": {
            "battery_pct": battery,
            "capabilities": {
                "nearby": True, "ble_gatt": False, "wifi_aware": False,
                "uwb": False, "camera": True, "gnss": True,
            },
            "app_version": "0.1.0",
        },
    }


def envelope(priv, bundle_id, pl, relay):
    raw = canonical(pl)
    pub = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "v": 1,
        "bundle_id": bundle_id,
        "payload_b64": base64.b64encode(raw).decode(),
        "payload_hash": hashlib.sha256(raw).hexdigest(),
        "signer_key_id": pseudonym(pub),
        "signer_pubkey_b64": base64.b64encode(pub).decode(),
        "signature": base64.b64encode(priv.sign(raw)).decode(),
        "relay": relay,
    }


def relay(hop=0, frm=None, transport="nearby", rssi=None, gw=None):
    return {"hop_count": hop, "received_from": frm, "transport": transport,
            "rssi": rssi, "gateway_position": gw}


def write(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  {name}")


def main():
    os.makedirs(OUT, exist_ok=True)
    priv = Ed25519PrivateKey.from_private_bytes(SEED)
    pub = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    node_a = pseudonym(pub)

    loc = {"lat": 4.6533, "lon": -74.0836, "accuracy_m": 12.0,
           "source": "gnss", "measured_at": "2026-08-22T17:03:41Z"}

    print("Generando fixtures en fixtures/ ...")

    # 1. valido, campos de evidencia aun vacios (estado del nucleo de 5 h)
    p1 = payload(3, "TRAPPED", created="2026-08-22T17:04:00Z", loc=loc, node=node_a)
    valid = envelope(priv, "0191f3a2-0000-7000-8000-000000000001", p1, relay())
    write("bundle-valid.json", valid)

    # 2. duplicado: mismo bundle_id, distinta metadata de relay -> un solo registro logico
    dup = json.loads(json.dumps(valid))
    dup["relay"] = relay(hop=2, frm=node_a, rssi=-67)
    write("bundle-duplicate.json", dup)

    # 3. manipulado: se altera un byte del payload -> hash y firma deben fallar
    tampered = json.loads(json.dumps(valid))
    raw = bytearray(base64.b64decode(tampered["payload_b64"]))
    i = raw.find(b'"TRAPPED"')
    raw[i:i + 9] = b'"SAFE"   '            # mismo largo, contenido distinto
    tampered["payload_b64"] = base64.b64encode(bytes(raw)).decode()
    write("bundle-tampered.json", tampered)

    # 4. vencido: TTL de 60 s con created_at antiguo
    p4 = payload(1, "HELP", created="2026-08-22T10:00:00Z", ttl_s=60, loc=loc, node=node_a)
    write("bundle-expired.json",
          envelope(priv, "0191f3a2-0000-7000-8000-000000000004", p4, relay()))

    # 5. con evidencia llena: la forma que tendra el bundle cuando D4 implemente
    #    los sensores. Existe para que D5 maquete el estado "con datos" desde ya.
    ev = {
        "motion": {"detected": True, "pattern": "deliberate_shake", "confidence": 0.82,
                   "window_s": 10, "provenance": "MEASURED",
                   "observed_at": "2026-08-22T17:05:10Z"},
        "ppg": {"hr_bpm": 112, "sqi": 0.71, "waveform_ref": None,
                "provenance": "DERIVED", "measured_at": "2026-08-22T17:05:30Z"},
        "peers": [{"node_pseudonym": "aQ91xR7kLm0p", "rssi": -67, "transport": "nearby",
                   "provenance": "MEASURED", "observed_at": "2026-08-22T17:05:02Z"}],
    }
    p5 = payload(4, "TRAPPED", created="2026-08-22T17:05:40Z", loc=loc,
                 evidence=ev, battery=61, node=node_a)
    write("bundle-with-evidence.json",
          envelope(priv, "0191f3a2-0000-7000-8000-000000000005", p5, relay(hop=1, frm=node_a, rssi=-58)))

    # 5b. SQI bajo: la senal PPG no alcanza calidad. El HR existe en el objeto
    #     pero NINGUNA capa puede presentarlo como dato. Fixture para probar
    #     que la app lo oculta y que la exportacion a rescatistas lo retiene.
    ev_bad = {
        "motion": None,
        "ppg": {"hr_bpm": 148, "sqi": 0.18, "waveform_ref": None,
                "provenance": "DERIVED", "measured_at": "2026-08-22T17:06:00Z"},
        "peers": [],
    }
    p5b = payload(5, "HELP", created="2026-08-22T17:06:10Z", loc=loc,
                  evidence=ev_bad, battery=12, node=node_a)
    write("bundle-low-sqi.json",
          envelope(priv, "0191f3a2-0000-7000-8000-00000000005b", p5b, relay()))

    # 6. suplantacion: un atacante re-firma un payload alterado con SU clave,
    #    pero conserva el signer_key_id de la victima. Debe rechazarse porque
    #    hash(su clave publica) != signer_key_id declarado.
    attacker = Ed25519PrivateKey.from_private_bytes(bytes(range(100, 132)))
    att_pub = attacker.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    p6 = payload(9, "SAFE", created="2026-08-22T17:09:00Z", loc=loc, node=node_a)
    raw6 = canonical(p6)
    write("bundle-forged-key.json", {
        "v": 1,
        "bundle_id": "0191f3a2-0000-7000-8000-000000000006",
        "payload_b64": base64.b64encode(raw6).decode(),
        "payload_hash": hashlib.sha256(raw6).hexdigest(),
        "signer_key_id": node_a,                                  # identidad robada
        "signer_pubkey_b64": base64.b64encode(att_pub).decode(),  # clave del atacante
        "signature": base64.b64encode(attacker.sign(raw6)).decode(),
        "relay": relay(hop=1, frm=node_a, rssi=-70),
    })

    write("signer-public-key.json", {
        "note": "Clave de DEMO, semilla determinista. Jamas usar en produccion.",
        "signer_key_id": node_a,
        "algorithm": "Ed25519",
        "public_key_b64": base64.b64encode(pub).decode(),
    })
    print(f"\nnode_pseudonym del firmante: {node_a}")


if __name__ == "__main__":
    sys.exit(main())
