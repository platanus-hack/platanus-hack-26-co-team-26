"""Genera los vectores dorados de protocol/test-vectors/bundles/.

Determinista: mismos valores de entrada siempre producen los mismos bytes.
Sirve para el test de round-trip Kotlin<->Python (protocol-ci.yml). No incluye
firma real (Ed25519) todavía -- signature queda como placeholder de 64 bytes de
ceros hasta que core/crypto/Identity.kt tenga una implementación real; cuando
la haya, regenerar este vector con una firma real y actualizar signatures/.
"""
import json
import sys
sys.path.insert(0, "services/shared/src/api/protocol")

from google.protobuf import json_format
from helius.v1 import bundle_pb2, status_pb2, motion_pb2, biomarker_pb2, observation_pb2, common_pb2

OUT = "protocol/test-vectors/bundles"
PLACEHOLDER_SIG = bytes(64)


def header(disaster_id: str, node_id: bytes, seq: int, priority) -> bundle_pb2.BundleHeader:
    h = bundle_pb2.BundleHeader()
    h.version = 1
    h.disaster_id = disaster_id
    h.bundle_id = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    h.node_id = node_id
    h.sequence = seq
    h.created_at = 1755878400000  # 2026-08-22T16:00:00Z en ms, fijo para reproducibilidad
    h.expires_at = 1755882000000
    h.hop_count = 0
    h.priority = priority
    h.clock.monotonic_ms = 123456
    return h


def write(name: str, bundle: bundle_pb2.Bundle):
    bin_bytes = bundle.SerializeToString()
    with open(f"{OUT}/{name}.bin", "wb") as f:
        f.write(bin_bytes)
    js = json_format.MessageToDict(bundle, preserving_proto_field_name=True)
    with open(f"{OUT}/{name}.json", "w") as f:
        json.dump(js, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print(f"{name}: {len(bin_bytes)} bytes")


# 1. status
b = bundle_pb2.Bundle()
b.header.CopyFrom(header("helius-golden-2026", b"\x01" * 8, 1, common_pb2.P1_LOCATION))
b.status.location.lat = 4.65123
b.status.location.lon = -74.08291
b.status.location.acc_m = 12.5
b.status.ts = 1755878400
b.status.source = "gnss"
b.status.response_state = common_pb2.TRAPPED
b.status.battery = 42
b.status.device_state = "foreground_service"
b.signature = PLACEHOLDER_SIG
write("status_trapped", b)

# 2. motion
b = bundle_pb2.Bundle()
b.header.CopyFrom(header("helius-golden-2026", b"\x02" * 8, 1, common_pb2.P1_LOCATION))
b.motion.purposeful_motion_confidence = 0.91
b.motion.pattern = "3-3"
b.motion.last_motion_ts = 1755878390
b.motion.activity_state = "PURPOSEFUL_MOTION"
b.signature = PLACEHOLDER_SIG
write("motion_purposeful", b)

# 3. biomarker
b = bundle_pb2.Bundle()
b.header.CopyFrom(header("helius-golden-2026", b"\x03" * 8, 1, common_pb2.P2_STATUS))
b.biomarker.pulse_bpm = 112.0
b.biomarker.pulse_ci_low = 105.0
b.biomarker.pulse_ci_high = 119.0
b.biomarker.sqi = 0.86
b.biomarker.source = "camera_ppg"
b.biomarker.model_version = "heuristic-fallback-v1"
b.biomarker.observed_at = 1755878395
b.biomarker.window_ms = 12000
b.signature = PLACEHOLDER_SIG
write("biomarker_pulse", b)

# 4. observation
b = bundle_pb2.Bundle()
b.header.CopyFrom(header("helius-golden-2026", b"\x04" * 8, 1, common_pb2.P3_NETWORK_OBS))
b.observation.incident_id = b"incident-2026-001"
b.observation.node_a = b"\x01" * 8
b.observation.node_b = b"\x02" * 8
b.observation.rssi_dbm = -78.0
b.observation.transport = "BLE"
b.observation.observed_at = 1755878396
b.signature = PLACEHOLDER_SIG
write("observation_peer", b)

# 5. raw (T2)
b = bundle_pb2.Bundle()
b.header.CopyFrom(header("helius-golden-2026", b"\x05" * 8, 1, common_pb2.P4_RAW_SENSOR))
b.raw.tier = "T2"
b.raw.chunk = bytes(range(32))
b.raw.chunk_index = 0
b.raw.chunk_count = 4
b.signature = PLACEHOLDER_SIG
write("raw_chunk", b)

print("OK: 5 vectores dorados generados en", OUT)
