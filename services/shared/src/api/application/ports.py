"""Puertos del backend (Sección 4.4) — interfaces que implementan los adaptadores.

Dueño: Miguel. Revisor: Helmut (CryptoVerifierPort — implementación real vive en core/crypto).
"""

from abc import ABC, abstractmethod


class AlertSourcePort(ABC):
    """Alertas de fuentes externas. Adaptadores: SgcAdapter, CapFeedAdapter, UsgsAdapter, ManualAdapter, FakeAdapter."""

    @abstractmethod
    async def poll(self) -> list[dict]: ...


class IncidentRepositoryPort(ABC):
    """Incidentes y zonas. Adaptadores: PostgisIncidentRepo, InMemory."""


class BundleRepositoryPort(ABC):
    """Bundles y evidencias. Adaptadores: PostgisBundleRepo, InMemory."""


class NodeRepositoryPort(ABC):
    """Nodos, identidades, encuentros. Adaptadores: PostgisNodeRepo."""


class ObservationRepositoryPort(ABC):
    """Observaciones RF. Adaptadores: PostgisObservationRepo."""


class LocalizationEnginePort(ABC):
    """Estimar zona probable. Adaptadores: FactorGraphEngine, NaiveCentroidEngine."""

    @abstractmethod
    async def estimate(self, node_id: str) -> dict: ...


class NotificationPort(ABC):
    """Push a dispositivos. Adaptadores: FcmAdapter, NoopAdapter."""


class EventBusPort(ABC):
    """Publicar cambios de estado. Adaptadores: RedisStreamsAdapter, InMemoryBus."""


class RealtimeChannelPort(ABC):
    """WebSocket hacia dashboards. Adaptadores: FastapiWsAdapter."""


class ObjectStoragePort(ABC):
    """RAW tier-2. Adaptadores: S3Adapter, LocalFsAdapter."""


class CryptoVerifierPort(ABC):
    """Verificación Ed25519. Adaptadores: LibsodiumAdapter."""

    @abstractmethod
    def verify(self, header: bytes, payload: bytes, signature: bytes, public_key: bytes) -> bool: ...


class AuditLogPort(ABC):
    """Trazabilidad de accesos a PII. Adaptadores: PostgresAuditLog."""

    @abstractmethod
    async def record(self, actor: str, subject: str, justification: str) -> None: ...
