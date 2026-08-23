"""SismoMesh — alert_ingestor: fuentes sísmicas externas → evento interno.

Hexágono independiente (ADR-0001), autocontenido. No importa `services/shared`
todavía: hoy mismo `pip install -e services/shared` falla (gtsam pineado a
numpy<2 choca con el numpy>=2.1 del propio kernel), un problema preexistente de
`services/localization` y ajeno a este servicio. Cuando eso se resuelva, el puerto
`AlertSourcePort` de aquí y el de `services/shared/src/api/application/ports.py`
deberían reconciliarse en uno solo — ver README.
"""

__version__ = "0.1.0"
