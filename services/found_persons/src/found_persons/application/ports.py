"""Puertos del hexágono `found_persons` (ADR-0001).

Regla del proyecto (CONTRIBUTING § Definition of Done): todo puerto nuevo trae
interfaz + adaptador real + *fake* determinista. Los reales viven en
`adapters/persistence/sqlite.py` y `adapters/crypto/`; los fakes, en
`adapters/persistence/memory.py` y `adapters/crypto/fake.py`.

Dueño: Miguel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from found_persons.domain.habeas_data import AuditEntry, Tombstone
from found_persons.domain.mesh import DeviceIdentity
from found_persons.domain.records import Claim, FoundPersonRecord, RecordQuery


class Clock(ABC):
    """Tiempo inyectable. Sin esto, ningún test de caducidad o de plazo legal sería
    determinista — y aquí casi todo depende de una fecha."""

    @abstractmethod
    def now_ms(self) -> int: ...


class IdGenerator(ABC):
    """Identificadores opacos. Nunca correlativos: un id secuencial filtra cuánta
    gente hay registrada y en qué orden apareció."""

    @abstractmethod
    def new_id(self, prefix: str) -> str: ...

    @abstractmethod
    def new_nonce(self) -> str: ...


class RecordRepository(ABC):
    """Persistencia de registros. Adaptadores: `SqliteRecordRepository`, `InMemory`."""

    @abstractmethod
    def get(self, record_id: str) -> FoundPersonRecord | None: ...

    @abstractmethod
    def find_by_lookup_token(
        self, incident_id: str, lookup_token: str
    ) -> FoundPersonRecord | None:
        """Búsqueda por token ciego. Es la única búsqueda por persona que existe:
        no hay `find_by_name` a propósito."""

    @abstractmethod
    def search(self, query: RecordQuery) -> tuple[list[FoundPersonRecord], int]:
        """Devuelve la página y el total, para que el listado pueda paginar sin
        volver a contar."""

    @abstractmethod
    def save(self, record: FoundPersonRecord) -> None: ...

    @abstractmethod
    def purge(self, record_id: str) -> None:
        """Borrado físico. Solo lo invoca el barrido de retención vencida."""

    @abstractmethod
    def due_for_anonymization(self, now_ms: int, limit: int = 100) -> list[FoundPersonRecord]: ...


class AuditLog(ABC):
    """`audit_log`. Regla de PII (§12.3, ADR-0007): se escribe ANTES de responder.

    No es una traza de depuración: es la prueba del deber de trazabilidad del
    Responsable (art. 17) y la fuente del derecho del Titular a saber quién accedió
    a su dato (art. 4 lit. e).
    """

    @abstractmethod
    def record(self, entry: AuditEntry) -> None: ...

    @abstractmethod
    def for_subject(self, subject_ref: str, limit: int = 200) -> list[AuditEntry]: ...

    @abstractmethod
    def count_for_actor_since(self, actor: str, since_ms: int) -> int:
        """Base del límite de tasa por dispositivo: se cuenta lo ya auditado, así el
        contador no puede divergir de la evidencia."""


class DeviceDirectory(ABC):
    """Dispositivos acreditados. Adaptadores: `SqliteDeviceDirectory`, `InMemory`."""

    @abstractmethod
    def get(self, device_id: str) -> DeviceIdentity | None: ...

    @abstractmethod
    def save(self, device: DeviceIdentity) -> None: ...

    @abstractmethod
    def list_for_incident(self, incident_id: str) -> list[DeviceIdentity]: ...


class TombstoneStore(ABC):
    """Lápidas de supresión, ordenadas por secuencia para sincronización incremental."""

    @abstractmethod
    def append(self, tombstone: Tombstone) -> None: ...

    @abstractmethod
    def since(self, incident_id: str, sequence: int, limit: int = 500) -> list[Tombstone]: ...

    @abstractmethod
    def next_sequence(self, incident_id: str) -> int: ...


class ClaimRepository(ABC):
    """Consultas y reclamos del Titular (art. 14 y 15), con sus plazos."""

    @abstractmethod
    def get(self, claim_id: str) -> Claim | None: ...

    @abstractmethod
    def save(self, claim: Claim) -> None: ...

    @abstractmethod
    def open_claims(self, now_ms: int) -> list[Claim]: ...


class NonceStore(ABC):
    """Anti-replay de consultas firmadas. Adaptadores: Redis en producción, memoria
    en tests. La ventana de retención debe cubrir la vigencia máxima de una consulta."""

    @abstractmethod
    def remember(self, nonce: str, expires_at_ms: int) -> bool:
        """`True` si el nonce era nuevo. `False` si ya se había usado."""


class SignatureVerifier(ABC):
    """Verificación Ed25519 de lo que firman los dispositivos.

    Espeja `CryptoVerifierPort` de `services/shared`: misma curva, mismo formato de
    clave, para que un bundle y una consulta se validen con la misma identidad.
    """

    @abstractmethod
    def verify(self, message: bytes, signature_b64u: str, public_key_b64u: str) -> bool: ...


class Signer(ABC):
    """Firma del servicio sobre cápsulas y lápidas. Es lo que permite a un teléfono
    confiar en algo que le llegó por un relay desconocido."""

    @abstractmethod
    def sign(self, message: bytes) -> str: ...

    @abstractmethod
    def public_key_b64u(self) -> str: ...


class PayloadSealer(ABC):
    """Cifrado hacia la clave del dispositivo destinatario.

    X25519 + HKDF + ChaCha20-Poly1305, igual que el handshake de transporte del
    modelo de amenazas. Los relays transportan bytes que no pueden leer.
    """

    @abstractmethod
    def seal(self, plaintext: bytes, recipient_kex_public_key_b64u: str) -> str: ...


class IncidentKeyProvider(ABC):
    """Clave HMAC por incidente para el token ciego.

    Es por incidente y no global para que el mismo documento produzca tokens
    distintos en desastres distintos: así el token no sirve para seguir a una
    persona a lo largo del tiempo.
    """

    @abstractmethod
    def key_for(self, incident_id: str) -> bytes: ...
