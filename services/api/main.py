"""SismoMesh - API de ingesta y consulta.

Nucleo de 5 h: SQLite (no PostGIS) y polling (no WebSocket). Ver docs/CORE-5H.md.
Levantar:  cd services/api && ../../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
"""
import base64, json, os, sqlite3, sys, time
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "protocol"))
from verify import Rejected, verify  # noqa: E402  fuente de verdad compartida

DB = os.environ.get("SISMOMESH_DB", os.path.join(os.path.dirname(__file__), "sismomesh.db"))
STATIC = os.path.join(os.path.dirname(__file__), "static")

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  incident_id TEXT PRIMARY KEY,
  name        TEXT,
  created_at  TEXT
);
CREATE TABLE IF NOT EXISTS bundles (
  bundle_id      TEXT PRIMARY KEY,          -- dedupe: mismo id -> un solo registro logico
  incident_id    TEXT NOT NULL,
  node_pseudonym TEXT NOT NULL,
  seq            INTEGER,
  created_at     TEXT,
  status         TEXT,
  lat REAL, lon REAL, accuracy_m REAL,
  battery_pct    INTEGER,
  hop_count      INTEGER,
  transport      TEXT,
  rssi           INTEGER,
  verified       INTEGER NOT NULL,
  reject_reason  TEXT,
  payload_json   TEXT,
  envelope_json  TEXT,
  received_at    REAL,
  times_seen     INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_bundles_incident ON bundles(incident_id, received_at);
-- Log append-only de rechazos. Tabla aparte a proposito: un payload manipulado
-- reusa el bundle_id de uno legitimo, asi que si dependieramos de la PK de
-- bundles el ataque se absorberia en silencio y nadie lo veria en el timeline.
CREATE TABLE IF NOT EXISTS rejections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bundle_id      TEXT,
  incident_id    TEXT,
  node_pseudonym TEXT,
  reason         TEXT,
  envelope_json  TEXT,
  received_at    REAL
);
CREATE INDEX IF NOT EXISTS idx_rej_incident ON rejections(incident_id, received_at);
CREATE TABLE IF NOT EXISTS idempotency (
  key TEXT PRIMARY KEY, response TEXT, created_at REAL
);
"""


@contextmanager
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


with db() as con:
    con.executescript(SCHEMA)

app = FastAPI(title="SismoMesh API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- ingesta

def ingest_one(con, env: dict) -> dict:
    """Verifica e inserta un bundle. Nunca lanza: devuelve el resultado."""
    bid = env.get("bundle_id")
    if not bid:
        return {"bundle_id": None, "result": "rejected", "reason": "sin bundle_id"}

    try:
        payload = verify(env)                      # integridad sobre los bytes recibidos
        verified, reason = True, None
    except (Rejected, KeyError, ValueError) as e:
        verified, reason = False, str(e)
        try:
            payload = json.loads(base64.b64decode(env.get("payload_b64", "")))
        except Exception:
            payload = {}

    # Un bundle rechazado se REGISTRA, no se descarta en silencio: el jurado
    # tiene que poder ver que la malla detecto el ataque.
    if not verified:
        con.execute(
            "INSERT INTO rejections (bundle_id, incident_id, node_pseudonym, reason,"
            " envelope_json, received_at) VALUES (?,?,?,?,?,?)",
            (bid, payload.get("incident_id", "unknown"), payload.get("node_pseudonym", "unknown"),
             reason, json.dumps(env), time.time()))
        return {"bundle_id": bid, "result": "rejected", "reason": reason}

    row = con.execute("SELECT hop_count FROM bundles WHERE bundle_id=?", (bid,)).fetchone()
    if row is not None:
        con.execute("UPDATE bundles SET times_seen = times_seen + 1 WHERE bundle_id=?", (bid,))
        return {"bundle_id": bid, "result": "duplicate"}

    loc = payload.get("location") or {}
    dev = payload.get("device") or {}
    rl = env.get("relay") or {}
    con.execute(
        "INSERT INTO bundles (bundle_id, incident_id, node_pseudonym, seq, created_at, status,"
        " lat, lon, accuracy_m, battery_pct, hop_count, transport, rssi, verified, payload_json,"
        " envelope_json, received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)",
        (bid, payload.get("incident_id"), payload.get("node_pseudonym"), payload.get("seq"),
         payload.get("created_at"), payload.get("status"), loc.get("lat"), loc.get("lon"),
         loc.get("accuracy_m"), dev.get("battery_pct"), rl.get("hop_count"), rl.get("transport"),
         rl.get("rssi"), json.dumps(payload), json.dumps(env), time.time()))
    con.execute("INSERT OR IGNORE INTO incidents VALUES (?,?,?)",
                (payload.get("incident_id"), payload.get("incident_id"), payload.get("created_at")))
    return {"bundle_id": bid, "result": "accepted"}


@app.post("/bundles/batch")
def post_batch(body: dict, idempotency_key: str | None = Header(default=None)):
    """Subida del gateway. Reintentar con la misma Idempotency-Key es seguro."""
    with db() as con:
        if idempotency_key:
            row = con.execute("SELECT response FROM idempotency WHERE key=?",
                              (idempotency_key,)).fetchone()
            if row:
                return {**json.loads(row["response"]), "replayed": True}

        results = [ingest_one(con, e) for e in body.get("bundles", [])]
        resp = {
            "received": len(results),
            "accepted": sum(r["result"] == "accepted" for r in results),
            "duplicates": sum(r["result"] == "duplicate" for r in results),
            "rejected": sum(r["result"] == "rejected" for r in results),
            "results": results,
        }
        if idempotency_key:
            con.execute("INSERT OR REPLACE INTO idempotency VALUES (?,?,?)",
                        (idempotency_key, json.dumps(resp), time.time()))
        return resp


# ---------------------------------------------------------------- consulta

@app.post("/incidents")
def post_incident(body: dict):
    iid = body.get("incident_id")
    if not iid:
        raise HTTPException(400, "incident_id requerido")
    with db() as con:
        con.execute("INSERT OR IGNORE INTO incidents VALUES (?,?,?)",
                    (iid, body.get("name", iid), body.get("created_at")))
    return {"incident_id": iid}


@app.get("/incidents")
def list_incidents():
    with db() as con:
        return {"incidents": [dict(r) for r in con.execute(
            "SELECT i.*, (SELECT COUNT(*) FROM bundles b WHERE b.incident_id=i.incident_id)"
            " AS bundle_count FROM incidents i").fetchall()]}


@app.get("/incidents/{incident_id}/nodes")
def get_nodes(incident_id: str):
    """Estado mas reciente por nodo. Solo bundles verificados."""
    with db() as con:
        rows = con.execute(
            "SELECT node_pseudonym, status, lat, lon, accuracy_m, battery_pct, hop_count,"
            " transport, rssi, MAX(created_at) AS last_seen, COUNT(*) AS bundles"
            " FROM bundles WHERE incident_id=? AND verified=1"
            " GROUP BY node_pseudonym", (incident_id,)).fetchall()
        return {"nodes": [dict(r) for r in rows]}


@app.get("/incidents/{incident_id}/bundles")
def get_bundles(incident_id: str, since: float = 0.0, limit: int = 200):
    """Timeline. `since` es el received_at devuelto en la llamada anterior."""
    with db() as con:
        rows = con.execute(
            "SELECT bundle_id, node_pseudonym, seq, created_at, status, lat, lon, battery_pct,"
            " hop_count, transport, rssi, verified, reject_reason, times_seen, received_at"
            " FROM bundles WHERE incident_id=? AND received_at > ?"
            " ORDER BY received_at DESC LIMIT ?", (incident_id, since, limit)).fetchall()
        out = [dict(r) for r in rows]
        return {"bundles": out, "cursor": max([b["received_at"] for b in out], default=since)}


@app.get("/incidents/{incident_id}/rejections")
def get_rejections(incident_id: str, limit: int = 100):
    """Intentos rechazados. Que la malla detecte el ataque es parte de la demo."""
    with db() as con:
        rows = con.execute(
            "SELECT id, bundle_id, node_pseudonym, reason, received_at FROM rejections"
            " WHERE incident_id=? OR incident_id='unknown' ORDER BY received_at DESC LIMIT ?",
            (incident_id, limit)).fetchall()
        return {"rejections": [dict(r) for r in rows]}


@app.get("/health")
def health():
    with db() as con:
        n = con.execute("SELECT COUNT(*) c FROM bundles").fetchone()["c"]
        r = con.execute("SELECT COUNT(*) c FROM rejections").fetchone()["c"]
    return {"status": "ok", "bundles": n, "rejections": r, "db": os.path.basename(DB)}


@app.post("/admin/reset")
def reset():
    """Reset del demo. Sin esto, la tercera corrida arranca con basura de la primera."""
    with db() as con:
        con.executescript("DELETE FROM bundles; DELETE FROM incidents;"
                          " DELETE FROM idempotency; DELETE FROM rejections;")
    return {"status": "reset"}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ------------------------------------------------- exportacion para rescatistas
# Requisito del equipo (no estaba en el playbook): entregar a Cruz Roja /
# organismos de socorro un listado priorizado y consumible con herramientas
# estandar. Tres formatos: JSON (integracion), CSV (planilla/radio) y GeoJSON
# (QGIS, Google Earth, uMap).

SQI_MIN = 0.5          # bajo esto no se exporta HR. Ver docs/CORE-5H.md.
STALE_S = 1800         # 30 min sin reporte -> el dato deja de ser accionable

TRIAGE = {"TRAPPED": (1, "CRITICO"), "HELP": (2, "ALTO"),
          "UNCONFIRMED": (3, "POR_CONFIRMAR"), "SAFE": (4, "ESTABLE")}


def _require_key(x_api_key: str | None):
    """Auth opcional: solo se exige si SISMOMESH_EXPORT_KEY esta definida.

    Asi el demo corre sin friccion y un despliegue real no queda abierto.
    """
    expected = os.environ.get("SISMOMESH_EXPORT_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(401, "X-API-Key invalida o ausente")


def build_triage(incident_id: str, max_rank: int) -> list[dict]:
    with db() as con:
        rows = con.execute(
            "SELECT b.* FROM bundles b JOIN (SELECT node_pseudonym, MAX(created_at) mx"
            "  FROM bundles WHERE incident_id=? AND verified=1 GROUP BY node_pseudonym) l"
            " ON b.node_pseudonym=l.node_pseudonym AND b.created_at=l.mx"
            " WHERE b.incident_id=? AND b.verified=1", (incident_id, incident_id)).fetchall()

    now = time.time()
    out = []
    for r in rows:
        pl = json.loads(r["payload_json"] or "{}")
        ev = pl.get("evidence") or {}
        rank, label = TRIAGE.get(r["status"], (3, "POR_CONFIRMAR"))

        try:
            age = now - __import__("datetime").datetime.fromisoformat(
                (pl.get("created_at") or "").replace("Z", "+00:00")).timestamp()
        except Exception:
            age = None

        # La prioridad sale UNICAMENTE del estado reportado. La antiguedad y la
        # bateria se informan como banderas, no degradan el rank: alguien que
        # reporto TRAPPED hace 5 h sigue atrapado, y una bateria agonizante es
        # razon para llegar antes, no despues.
        notes = []
        vigente = True
        if age is not None and age > STALE_S:
            notes.append(f"sin reporte hace {int(age // 60)} min")
            vigente = False
        if (r["battery_pct"] or 100) < 15:
            notes.append("bateria critica: puede dejar de reportar")
        if r["lat"] is None:
            notes.append("sin ubicacion")

        # PPG: solo se exporta HR si el SQI lo respalda. La regla de calidad
        # vive tambien en el borde de salida, no solo en la app.
        ppg = ev.get("ppg") or {}
        sqi = ppg.get("sqi")
        hr = ppg.get("hr_bpm") if (sqi is not None and sqi >= SQI_MIN) else None
        if ppg and hr is None:
            notes.append("PPG descartado por señal insuficiente")

        mot = ev.get("motion") or {}
        out.append({
            "triage": label,
            "triage_rank": rank,
            "dato_vigente": vigente,
            "node_pseudonym": r["node_pseudonym"],
            "estado_reportado": r["status"],
            "autoreportado": bool(pl.get("user_reported")),
            "lat": r["lat"], "lon": r["lon"], "precision_m": r["accuracy_m"],
            "ultimo_reporte_utc": pl.get("created_at"),
            "antiguedad_s": None if age is None else int(age),
            "bateria_pct": r["battery_pct"],
            "saltos": r["hop_count"], "via": r["transport"], "rssi": r["rssi"],
            "movimiento_detectado": mot.get("detected"),
            "movimiento_confianza": mot.get("confidence"),
            "fc_bpm": hr, "fc_sqi": sqi,
            "integridad": "firma_verificada",
            "observaciones": "; ".join(notes) or None,
        })

    out.sort(key=lambda x: (x["triage_rank"], x["antiguedad_s"] if x["antiguedad_s"] is not None else 1e9))
    return [x for x in out if x["triage_rank"] <= max_rank]


DISCLAIMER = (
    "Datos autorreportados y evidencia derivada de sensores de telefono. "
    "NO constituyen diagnostico clinico ni confirmacion de ubicacion exacta. "
    "Verificar en terreno antes de asignar recursos."
)


@app.get("/incidents/{incident_id}/triage")
def triage_json(incident_id: str, max_rank: int = 4, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    rows = build_triage(incident_id, max_rank)
    return {
        "incident_id": incident_id,
        "generado_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "total": len(rows),
        "criticos": sum(r["triage_rank"] == 1 for r in rows),
        "advertencia": DISCLAIMER,
        "personas": rows,
    }


@app.get("/incidents/{incident_id}/triage.csv")
def triage_csv(incident_id: str, max_rank: int = 4, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    import csv, io as _io
    rows = build_triage(incident_id, max_rank)
    cols = ["triage", "node_pseudonym", "estado_reportado", "dato_vigente", "lat", "lon",
            "precision_m", "ultimo_reporte_utc", "antiguedad_s", "bateria_pct", "saltos",
            "via", "movimiento_detectado", "fc_bpm", "fc_sqi", "integridad", "observaciones"]
    buf = _io.StringIO()
    buf.write(f"# {DISCLAIMER}\n")
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    # "si"/"no"/"" en vez de True/False/None: lo lee un humano en una planilla,
    # y una celda vacia debe significar "sin dato", no "no".
    b = {True: "si", False: "no", None: ""}
    w.writerows([{k: (b[v] if isinstance(v, bool) or v is None and k in
                      ("dato_vigente", "movimiento_detectado", "autoreportado") else v)
                  for k, v in r.items()} for r in rows])
    from fastapi.responses import Response
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             f'attachment; filename="triage-{incident_id}.csv"'})


@app.get("/incidents/{incident_id}/triage.geojson")
def triage_geojson(incident_id: str, max_rank: int = 4,
                   x_api_key: str | None = Header(default=None)):
    """Consumible directo por QGIS, Google Earth y uMap."""
    _require_key(x_api_key)
    rows = [r for r in build_triage(incident_id, max_rank) if r["lat"] is not None]
    return {
        "type": "FeatureCollection",
        "properties": {"incident_id": incident_id, "advertencia": DISCLAIMER},
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": r,
        } for r in rows],
    }
