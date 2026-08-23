"""Divulgación entre dispositivos: acreditar, responder consultas firmadas, propagar lápidas.

Este es el caso de uso que el resto del servicio existe para habilitar. Un teléfono
en zona pregunta por alguien; la respuesta puede tener que cruzar teléfonos ajenos
antes de llegar. Todo lo que sigue está diseñado para que eso no equivalga a
repartir datos personales por el camino.

Decisión de diseño que conviene tener presente al leer: para los ámbitos bajos
(`PUBLIC`, `FAMILY`) **no se distingue** "no hay registro" de "hay registro pero no
te corresponde". Ambas devuelven `no_disclosure`. Si se distinguieran, la API sería
un oráculo de existencia: cualquiera con un documento ajeno podría averiguar si esa
persona está o no en el sistema, que es justo el dato que no debe poder deducirse.
Los ámbitos acreditados (`RESPONDER`, `AUTHORITY`) sí reciben la verdad operativa,
porque responden por ella ante la autoridad del incidente.

Dueño: Miguel. Revisor obligatorio: Helmut (firma, sellado y transporte DTN).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from found_persons.application.context import AccessContext, Principal
from found_persons.application.ports import (
    AuditLog,
    Clock,
    DeviceDirectory,
    IdGenerator,
    NonceStore,
    PayloadSealer,
    RecordRepository,
    SignatureVerifier,
    Signer,
    TombstoneStore,
)
from found_persons.domain.canonical import b64u, canonical_bytes
from found_persons.domain.errors import (
    DeviceQuotaExceeded,
    HabeasDataViolation,
    InvalidSignature,
    ReplayedRequest,
    UnknownDevice,
)
from found_persons.domain.habeas_data import (
    AuditEntry,
    DisclosureScope,
    LegalBasis,
    Tombstone,
)
from found_persons.domain.mesh import DeviceIdentity, DeviceQuery, DisclosureCapsule
from found_persons.domain.policies import (
    DEVICE_HOURLY_QUOTA,
    DisclosureView,
    capsule_expiry,
    decide,
    project,
)
from found_persons.domain.vocabulary import RecordLifecycle

#: Ámbitos a los que se les responde igual exista o no el registro. Ver el docstring
#: del módulo: evitar el oráculo de existencia es un requisito, no una precaución.
UNIFORM_NEGATIVE_SCOPES: frozenset[DisclosureScope] = frozenset(
    {DisclosureScope.PUBLIC, DisclosureScope.FAMILY}
)

#: Respuesta única para esos ámbitos. Deliberadamente incapaz de distinguir casos.
UNIFORM_NEGATIVE_REASON = (
    "No hay novedad divulgable para este token en el ámbito de este dispositivo. "
    "Esta misma respuesta se entrega exista o no un registro, para que la consulta "
    "no permita deducir si una persona está o no en el sistema "
    "(Ley 1581 art. 4 lit. f, principio de acceso restringido)."
)

#: Margen tolerado de reloj adelantado. Los teléfonos de la malla no tienen hora
#: sincronizada — ver `ClockEvidence` en :core:domain.
CLOCK_SKEW_TOLERANCE_MS = 5 * 60_000

#: Vigencia máxima que puede declarar una consulta. Una consulta firmada con un año
#: de validez es una credencial permanente disfrazada.
MAX_QUERY_VALIDITY_MS = 15 * 60_000


@dataclass(frozen=True, slots=True)
class DeviceRegistration:
    """Acreditación de un teléfono. La otorga un principal con ámbito AUTHORITY."""

    device_id: str
    incident_id: str
    signing_public_key: str
    scope: DisclosureScope
    kex_public_key: str | None = None
    organization: str | None = None
    holder_ref: str | None = None
    expires_at: int | None = None


@dataclass(frozen=True, slots=True)
class CapsuleVerdict:
    """Resultado de revalidar una cápsula que llegó por la malla."""

    signature_valid: bool
    fresh: bool
    superseded: bool
    """Hay una lápida o una versión más nueva: la copia local debe descartarse."""
    must_delete: bool
    reasons: tuple[str, ...]
    current_tombstone_sequence: int


class MeshDisclosureService:
    def __init__(
        self,
        *,
        repository: RecordRepository,
        devices: DeviceDirectory,
        audit: AuditLog,
        tombstones: TombstoneStore,
        nonces: NonceStore,
        clock: Clock,
        ids: IdGenerator,
        signer: Signer,
        verifier: SignatureVerifier,
        sealer: PayloadSealer,
    ) -> None:
        self._repo = repository
        self._devices = devices
        self._audit = audit
        self._tombstones = tombstones
        self._nonces = nonces
        self._clock = clock
        self._ids = ids
        self._signer = signer
        self._verifier = verifier
        self._sealer = sealer

    # ------------------------------------------------------------------ #
    # Acreditación                                                        #
    # ------------------------------------------------------------------ #

    def register_device(
        self, registration: DeviceRegistration, *, principal: Principal
    ) -> DeviceIdentity:
        """Acredita un teléfono. Solo la autoridad del incidente puede hacerlo.

        Que la acreditación tenga dueño y fecha no es burocracia: es lo que permite
        responder "quién autorizó a este aparato a ver esto" cuando alguien lo
        pregunte, y revocarlo por persona y no solo por número de serie.
        """
        if principal.scope is not DisclosureScope.AUTHORITY:
            raise HabeasDataViolation(
                "Solo la autoridad del incidente acredita dispositivos. Permitir que "
                "un respondiente acredite a otros haría imposible saber quién "
                "respondió por cada acceso (Ley 1581 art. 17)."
            )
        if registration.scope is DisclosureScope.AUTHORITY:
            raise HabeasDataViolation(
                "No se acredita un dispositivo móvil con ámbito AUTHORITY: un teléfono "
                "extraviado no puede llevar consigo el acceso total al incidente."
            )

        now = self._clock.now_ms()
        device = DeviceIdentity(
            device_id=registration.device_id,
            incident_id=registration.incident_id,
            signing_public_key=registration.signing_public_key,
            kex_public_key=registration.kex_public_key,
            scope=registration.scope,
            accredited_by=principal.actor_id,
            accredited_at=now,
            organization=registration.organization,
            holder_ref=registration.holder_ref,
            expires_at=registration.expires_at,
        )
        self._devices.save(device)
        return device

    def revoke_device(
        self, device_id: str, *, reason: str, principal: Principal
    ) -> DeviceIdentity:
        """Retira la acreditación. Teléfono perdido, turno terminado, incidente cerrado."""
        if principal.scope is not DisclosureScope.AUTHORITY:
            raise HabeasDataViolation("Solo la autoridad del incidente revoca dispositivos.")
        device = self._devices.get(device_id)
        if device is None:
            raise UnknownDevice(f"Dispositivo '{device_id}' no acreditado.")
        revoked = replace(
            device, revoked_at=self._clock.now_ms(), revocation_reason=reason
        )
        self._devices.save(revoked)
        return revoked

    # ------------------------------------------------------------------ #
    # Consulta firmada dispositivo → servicio                             #
    # ------------------------------------------------------------------ #

    def answer(self, query: DeviceQuery) -> DisclosureCapsule:
        """Responde una consulta firmada con una cápsula minimizada, sellada y caducable."""
        now = self._clock.now_ms()
        device = self._authenticate(query, now_ms=now)

        record = self._repo.find_by_lookup_token(query.incident_id, query.lookup_token)
        principal = Principal(
            actor_id=f"device:{device.device_id}",
            scope=device.scope,
            organization=device.organization,
            channel="mesh",
            device_id=device.device_id,
        )
        context = AccessContext(
            purpose=query.purpose, justification=query.justification
        )

        # --- caso negativo -------------------------------------------------
        if record is None or not record.is_readable:
            outcome, reasons = self._negative_outcome(device.scope, record)
            audit_id = self._audit_mesh(
                principal=principal,
                context=context,
                subject_ref=record.id if record else f"token:{query.lookup_token}",
                categories=frozenset(),
                outcome="denied",
                legal_basis=record.consent.legal_basis if record else None,
            )
            return self._seal_and_sign(
                device=device,
                incident_id=query.incident_id,
                purpose=query.purpose,
                outcome=outcome,
                view=None,
                reasons=reasons,
                record_id=None,
                record_version=None,
                audit_id=audit_id,
                now_ms=now,
            )

        # --- decisión ------------------------------------------------------
        decision = decide(
            record, scope=device.scope, purpose=query.purpose, now_ms=now
        )

        # audit_log ANTES de construir la respuesta (regla de PII §12.3).
        audit_id = self._audit_mesh(
            principal=principal,
            context=context,
            subject_ref=record.id,
            categories=decision.categories,
            outcome=decision.outcome,
            legal_basis=record.consent.legal_basis,
        )

        if not decision.granted:
            outcome, reasons = self._negative_outcome(
                device.scope, record, denial_reasons=decision.reasons
            )
            return self._seal_and_sign(
                device=device,
                incident_id=query.incident_id,
                purpose=query.purpose,
                outcome=outcome,
                view=None,
                reasons=reasons,
                record_id=record.id if device.scope not in UNIFORM_NEGATIVE_SCOPES else None,
                record_version=None,
                audit_id=audit_id,
                now_ms=now,
            )

        return self._seal_and_sign(
            device=device,
            incident_id=query.incident_id,
            purpose=query.purpose,
            outcome="granted",
            view=project(record, decision),
            reasons=decision.reasons,
            record_id=record.id,
            record_version=record.version,
            audit_id=audit_id,
            now_ms=now,
        )

    # ------------------------------------------------------------------ #
    # Revalidación y lápidas                                              #
    # ------------------------------------------------------------------ #

    def verify_capsule(self, capsule: DisclosureCapsule) -> CapsuleVerdict:
        """Revalida una cápsula que un dispositivo recibió por la malla.

        Un teléfono puede verificar la firma por su cuenta con la clave pública del
        servicio; lo que no puede saber estando aislado es si el dato fue suprimido
        o rectificado después. Este endpoint es lo primero que debería llamar al
        recuperar conectividad.
        """
        now = self._clock.now_ms()
        reasons: list[str] = []

        signature_valid = self._verifier.verify(
            capsule.signing_bytes(), capsule.signature, self._signer.public_key_b64u()
        )
        if not signature_valid:
            reasons.append(
                "La firma no corresponde a este servicio: la cápsula fue alterada en "
                "tránsito o la fabricó un relay. Descártela."
            )

        fresh = capsule.is_fresh(now)
        if not fresh:
            reasons.append(
                "La cápsula caducó. El dato de emergencia no sobrevive a la emergencia "
                "(Ley 1581 art. 4 lit. c)."
            )

        superseded = False
        if capsule.record_id:
            current = self._repo.get(capsule.record_id)
            if current is None or current.lifecycle is RecordLifecycle.ERASED:
                superseded = True
                reasons.append(
                    "El Titular ejerció la supresión sobre este registro. Elimine la "
                    "copia local (Ley 1581 art. 8 lit. e)."
                )
            elif (
                capsule.record_version is not None
                and current.version > capsule.record_version
            ):
                superseded = True
                reasons.append(
                    f"Existe una versión más reciente (v{current.version} frente a "
                    f"v{capsule.record_version}). Su copia quedó desactualizada."
                )

        return CapsuleVerdict(
            signature_valid=signature_valid,
            fresh=fresh,
            superseded=superseded,
            must_delete=(not signature_valid) or (not fresh) or superseded,
            reasons=tuple(reasons),
            current_tombstone_sequence=self._tombstones.next_sequence(
                capsule.incident_id
            )
            - 1,
        )

    def tombstones_since(
        self, incident_id: str, *, sequence: int, limit: int = 500
    ) -> list[Tombstone]:
        """Lápidas nuevas desde una secuencia. Sincronización incremental para la malla.

        No lleva PII: solo `record_id` y motivo. Un dispositivo que nunca recibió una
        cápsula de ese registro no aprende nada de la lápida, porque no tiene con qué
        relacionar el identificador.
        """
        return self._tombstones.since(incident_id, sequence, limit=limit)

    # ------------------------------------------------------------------ #
    # Interno                                                             #
    # ------------------------------------------------------------------ #

    def _authenticate(self, query: DeviceQuery, *, now_ms: int) -> DeviceIdentity:
        device = self._devices.get(query.device_id)
        if device is None:
            raise UnknownDevice(
                f"El dispositivo '{query.device_id}' no está acreditado en este incidente."
            )
        if not device.is_active(now_ms):
            raise UnknownDevice(
                "La acreditación del dispositivo está revocada o vencida.",
                details=[device.revocation_reason or "acreditación caducada"],
            )
        if device.incident_id != query.incident_id:
            raise UnknownDevice(
                "El dispositivo está acreditado para otro incidente. Una acreditación "
                "no se transfiere entre emergencias."
            )

        if query.expires_at <= now_ms:
            raise ReplayedRequest("La consulta firmada ya caducó.")
        if query.issued_at > now_ms + CLOCK_SKEW_TOLERANCE_MS:
            raise ReplayedRequest("La consulta viene fechada en el futuro.")
        if query.expires_at - query.issued_at > MAX_QUERY_VALIDITY_MS:
            raise ReplayedRequest(
                "La consulta declara una vigencia mayor a la permitida: una consulta "
                "firmada de larga duración es una credencial permanente encubierta."
            )
        if not query.justification.strip():
            raise HabeasDataViolation(
                "La consulta no trae justificación. El Titular tiene derecho a saber "
                "por qué se accedió a su dato (Ley 1581 art. 4 lit. e)."
            )

        if not self._verifier.verify(
            query.signing_bytes(), query.signature, device.signing_public_key
        ):
            raise InvalidSignature(
                "La firma de la consulta no corresponde a la identidad acreditada."
            )

        if not self._nonces.remember(query.nonce, query.expires_at):
            raise ReplayedRequest(
                "Nonce ya utilizado: alguien está reenviando una consulta ajena."
            )

        used = self._audit.count_for_actor_since(
            f"device:{device.device_id}", now_ms - 3_600_000
        )
        if used >= DEVICE_HOURLY_QUOTA:
            raise DeviceQuotaExceeded(
                f"El dispositivo superó el límite de {DEVICE_HOURLY_QUOTA} consultas "
                "por hora. Un teléfono legítimo pregunta por la gente que conoce; "
                "este patrón parece recolección masiva."
            )

        return device

    def _negative_outcome(
        self,
        scope: DisclosureScope,
        record,
        *,
        denial_reasons: tuple[str, ...] = (),
    ) -> tuple[str, tuple[str, ...]]:
        """Uniformiza la respuesta negativa para los ámbitos que no deben distinguir."""
        if scope in UNIFORM_NEGATIVE_SCOPES:
            return "no_disclosure", (UNIFORM_NEGATIVE_REASON,)
        if record is None:
            return "not_found", (
                "No hay registro asociado a ese token en este incidente.",
            )
        if record.lifecycle is RecordLifecycle.ERASED:
            return "erased", (
                "El Titular ejerció la supresión. Elimine cualquier copia local.",
            )
        if record.lifecycle is RecordLifecycle.ANONYMIZED:
            return "erased", ("Venció la retención del dato operativo.",)
        return "denied", denial_reasons or (
            "La divulgación no está habilitada para este ámbito.",
        )

    def _seal_and_sign(
        self,
        *,
        device: DeviceIdentity,
        incident_id: str,
        purpose,
        outcome: str,
        view: DisclosureView | None,
        reasons: tuple[str, ...],
        record_id: str | None,
        record_version: int | None,
        audit_id: str,
        now_ms: int,
    ) -> DisclosureCapsule:
        """Serializa, cifra hacia el destinatario y firma. En ese orden."""
        body = _view_to_dict(view) if view is not None else {}
        plaintext = canonical_bytes(body)

        if device.kex_public_key:
            payload = self._sealer.seal(plaintext, device.kex_public_key)
            encrypted = True
        else:
            # Sin clave X25519 publicada no hay a quién cifrar. Se entrega en claro y
            # se prohíbe el reenvío: al menos no atraviesa relays ajenos.
            payload = b64u(plaintext)
            encrypted = False

        capsule = DisclosureCapsule(
            capsule_id=self._ids.new_id("cap"),
            incident_id=incident_id,
            audience_device_id=device.device_id,
            scope=device.scope,
            purpose=purpose,
            outcome=outcome,
            issued_at=now_ms,
            expires_at=capsule_expiry(device.scope, now_ms),
            payload=payload,
            payload_encrypted=encrypted,
            record_id=record_id,
            record_version=record_version,
            reasons=reasons,
            audit_id=audit_id,
            max_hops=4 if encrypted else 1,
            retransmit_allowed=encrypted,
        )
        return replace(capsule, signature=self._signer.sign(capsule.signing_bytes()))

    def _audit_mesh(
        self,
        *,
        principal: Principal,
        context: AccessContext,
        subject_ref: str,
        categories,
        outcome: str,
        legal_basis: LegalBasis | None,
    ) -> str:
        entry = AuditEntry(
            id=self._ids.new_id("aud"),
            occurred_at=self._clock.now_ms(),
            actor=principal.actor_id,
            actor_scope=principal.scope,
            subject_ref=subject_ref,
            action="mesh_disclose",
            purpose=context.purpose,
            justification=context.justification,
            legal_basis=legal_basis or LegalBasis.VITAL_INTEREST_INCAPACITY,
            categories_disclosed=frozenset(categories),
            outcome=outcome,
            channel="mesh",
        )
        self._audit.record(entry)
        return entry.id


def _view_to_dict(view: DisclosureView) -> dict:
    """Aplana la vista para la cápsula. Omite lo nulo: en la malla los bytes cuestan."""
    raw = {
        "record_id": view.record_id,
        "incident_id": view.incident_id,
        "status": view.status.value,
        "verification": view.verification.value,
        "found_at": view.found_at,
        "updated_at": view.updated_at,
        "version": view.version,
        "scope": view.scope.value,
        "categories": sorted(c.value for c in view.categories),
        "display_name": view.display_name,
        "initials": view.initials,
        "document_type": view.document_type,
        "document_number": view.document_number,
        "is_minor": view.is_minor,
        "site_name": view.site_name,
        "site_type": view.site_type,
        "municipality": view.municipality,
        "address": view.address,
        "lat": view.lat,
        "lon": view.lon,
        "contacts": [dict(c) for c in view.contacts] or None,
        "care_notes": view.care_notes,
        "biometric_ref": view.biometric_ref,
        "withheld": list(view.withheld) or None,
    }
    return {k: v for k, v in raw.items() if v is not None}
