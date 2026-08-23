"""Derechos del Titular (Ley 1581 art. 8): acceso, rectificación, revocación, supresión.

Una API que solo permita crear y leer registros no cumple la ley aunque minimice
perfectamente. El art. 8 le da al Titular derechos concretos y el art. 17 le impone
al Responsable el deber de habilitarlos. Estos son esos derechos, uno por método:

| Derecho (art. 8)                          | Aquí                       |
|-------------------------------------------|----------------------------|
| lit. a — conocer, actualizar, rectificar   | `RecordsService.replace`   |
| lit. b — prueba de la autorización         | `proof_of_consent`         |
| lit. c — ser informado del uso             | `access_history`           |
| lit. d — quejarse ante la SIC              | `privacy_notice`           |
| lit. e — revocar y suprimir                | `revoke_consent`, `erase`  |
| lit. f — acceder gratuitamente             | sin costo ni límite útil   |

Dueño: Miguel.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from found_persons.application.context import AccessContext, Principal
from found_persons.application.ports import (
    AuditLog,
    ClaimRepository,
    Clock,
    IdGenerator,
    RecordRepository,
    Signer,
    TombstoneStore,
)
from found_persons.domain.canonical import canonical_bytes
from found_persons.domain.deadlines import deadline_for, extension_for
from found_persons.domain.errors import (
    DomainError,
    HabeasDataViolation,
    RecordNotFound,
)
from found_persons.domain.habeas_data import (
    AuditEntry,
    Consent,
    Controller,
    DisclosureScope,
    Purpose,
    Tombstone,
    TombstoneReason,
)
from found_persons.domain.records import Claim, FoundPersonRecord
from found_persons.domain.vocabulary import RecordLifecycle


@dataclass(frozen=True, slots=True)
class ConsentProofView:
    """Lo que se le entrega al Titular cuando pide prueba de su autorización."""

    record_id: str
    legal_basis: str
    legal_basis_explained: str
    granted_by: str
    granted_at: int
    channel: str
    purposes: tuple[str, ...]
    categories: tuple[str, ...]
    scopes: tuple[str, ...]
    justification: str
    evidence_sha256: str | None
    evidence_uri: str | None
    expires_at: int | None
    revoked_at: int | None
    controller: Controller


#: Explicación en lenguaje llano de cada causal. El deber de informar (art. 12) no
#: se cumple citando un artículo: se cumple diciéndole a la persona qué pasó con su
#: dato en términos que entienda.
BASIS_EXPLANATIONS: dict[str, str] = {
    "subject_consent": (
        "Usted autorizó expresamente el tratamiento de sus datos."
    ),
    "legal_guardian_consent": (
        "Su representante legal autorizó el tratamiento en su nombre."
    ),
    "vital_interest_incapacity": (
        "Sus datos se trataron sin autorización previa porque era necesario para "
        "proteger su interés vital y usted no estaba en condiciones de autorizarlo "
        "(Ley 1581 de 2012, artículo 6, literal b). Puede revocar esta base y pedir "
        "la supresión en cualquier momento."
    ),
    "health_emergency": (
        "Sus datos se trataron por tratarse de una urgencia sanitaria, caso en que "
        "la ley no exige autorización previa (Ley 1581 de 2012, artículo 10, literal c)."
    ),
    "public_authority_duty": (
        "Una entidad pública requirió sus datos en ejercicio de sus funciones legales "
        "(Ley 1581 de 2012, artículo 10, literal a)."
    ),
}


class DataSubjectRightsService:
    def __init__(
        self,
        *,
        repository: RecordRepository,
        audit: AuditLog,
        claims: ClaimRepository,
        tombstones: TombstoneStore,
        clock: Clock,
        ids: IdGenerator,
        signer: Signer,
        holidays: frozenset[date] = frozenset(),
    ) -> None:
        self._repo = repository
        self._audit = audit
        self._claims = claims
        self._tombstones = tombstones
        self._clock = clock
        self._ids = ids
        self._signer = signer
        self._holidays = holidays

    # ------------------------------------------------------------------ #
    # Art. 8 lit. c — saber quién usó mi dato                             #
    # ------------------------------------------------------------------ #

    def access_history(
        self, record_id: str, *, principal: Principal, context: AccessContext
    ) -> list[AuditEntry]:
        """Historial de accesos al registro.

        Es el derecho más incómodo de implementar y el más útil de todos: convierte
        la promesa de trazabilidad en algo que el Titular puede leer. Funciona
        incluso sobre registros suprimidos, porque saber quién vio su dato antes de
        borrarlo sigue siendo su derecho.
        """
        record = self._repo.get(record_id)
        if record is None:
            raise RecordNotFound(f"No existe el registro '{record_id}'.")

        self._audit.record(
            AuditEntry(
                id=self._ids.new_id("aud"),
                occurred_at=self._clock.now_ms(),
                actor=principal.actor_id,
                actor_scope=principal.scope,
                subject_ref=record_id,
                action="read_access_history",
                purpose=context.purpose,
                justification=context.justification
                or "Ejercicio del derecho a ser informado (art. 8 lit. c).",
                legal_basis=record.consent.legal_basis,
                outcome="granted",
                channel=principal.channel,
            )
        )
        return self._audit.for_subject(record_id)

    # ------------------------------------------------------------------ #
    # Art. 8 lit. b — prueba de la autorización                           #
    # ------------------------------------------------------------------ #

    def proof_of_consent(
        self, record_id: str, *, principal: Principal, context: AccessContext
    ) -> ConsentProofView:
        """Prueba de la autorización otorgada, o de la causal invocada en su lugar."""
        record = self._require(record_id)
        consent = record.consent
        self._audit.record(
            AuditEntry(
                id=self._ids.new_id("aud"),
                occurred_at=self._clock.now_ms(),
                actor=principal.actor_id,
                actor_scope=principal.scope,
                subject_ref=record_id,
                action="read_consent_proof",
                purpose=context.purpose,
                justification=context.justification
                or "Solicitud de prueba de la autorización (art. 8 lit. b).",
                legal_basis=consent.legal_basis,
                outcome="granted",
                channel=principal.channel,
            )
        )
        return ConsentProofView(
            record_id=record.id,
            legal_basis=consent.legal_basis.value,
            legal_basis_explained=BASIS_EXPLANATIONS.get(
                consent.legal_basis.value, ""
            ),
            granted_by=consent.proof.captured_by,
            granted_at=consent.proof.captured_at,
            channel=consent.proof.channel,
            purposes=tuple(sorted(p.value for p in consent.purposes)),
            categories=tuple(sorted(c.value for c in consent.categories)),
            scopes=tuple(sorted(s.value for s in consent.scopes)),
            justification=consent.proof.justification,
            evidence_sha256=consent.proof.evidence_sha256,
            evidence_uri=consent.proof.evidence_uri,
            expires_at=consent.expires_at,
            revoked_at=consent.revoked_at,
            controller=record.controller,
        )

    # ------------------------------------------------------------------ #
    # Art. 8 lit. e — revocar                                             #
    # ------------------------------------------------------------------ #

    def revoke_consent(
        self,
        record_id: str,
        *,
        reason: str,
        principal: Principal,
        context: AccessContext,
    ) -> FoundPersonRecord:
        """Revoca la autorización. El registro deja de ser divulgable de inmediato.

        Revocar no es suprimir: el dato sigue existiendo (puede haber deberes de
        conservación), pero ninguna consulta vuelve a obtenerlo. Se emite lápida
        para que las copias que ya salieron por la malla también dejen de servir.
        """
        record = self._require(record_id)
        if record.consent.revoked_at is not None:
            return record

        now = self._clock.now_ms()
        revoked = replace(record, consent=record.consent.revoked(at_ms=now, reason=reason), updated_at=now, version=record.version + 1)

        self._audit.record(
            AuditEntry(
                id=self._ids.new_id("aud"),
                occurred_at=now,
                actor=principal.actor_id,
                actor_scope=principal.scope,
                subject_ref=record_id,
                action="revoke_consent",
                purpose=context.purpose,
                justification=reason,
                legal_basis=record.consent.legal_basis,
                outcome="granted",
                channel=principal.channel,
            )
        )
        self._repo.save(revoked)
        self._emit_tombstone(
            revoked, reason=TombstoneReason.CONSENT_REVOKED, now_ms=now
        )
        return revoked

    def update_consent(
        self,
        record_id: str,
        new_consent: Consent,
        *,
        principal: Principal,
        context: AccessContext,
    ) -> FoundPersonRecord:
        """Ajusta la autorización granular: qué categorías, para qué y hacia quién.

        Es el camino normal cuando la persona recupera la capacidad de decidir: se
        entró por interés vital y ahora ella misma dice qué autoriza. Estrechar
        siempre se puede; ampliar exige una autorización nueva, no una edición.
        """
        record = self._require(record_id)
        now = self._clock.now_ms()

        if record.consent.revoked_at is not None:
            raise HabeasDataViolation(
                "La autorización fue revocada. Para volver a tratar el dato hace "
                "falta una autorización nueva del Titular, no una modificación de "
                "la anterior (Ley 1581 art. 9)."
            )

        candidate = replace(
            record, consent=new_consent, updated_at=now, version=record.version + 1
        )
        problems = candidate.validate()
        if problems:
            raise HabeasDataViolation(
                "La autorización propuesta dejaría el registro fuera de la ley.",
                details=problems,
            )

        self._audit.record(
            AuditEntry(
                id=self._ids.new_id("aud"),
                occurred_at=now,
                actor=principal.actor_id,
                actor_scope=principal.scope,
                subject_ref=record_id,
                action="update_consent",
                purpose=context.purpose,
                justification=context.justification,
                legal_basis=new_consent.legal_basis,
                outcome="granted",
                channel=principal.channel,
            )
        )
        self._repo.save(candidate)
        self._emit_tombstone(
            candidate, reason=TombstoneReason.RECTIFIED, now_ms=now
        )
        return candidate

    # ------------------------------------------------------------------ #
    # Art. 14 y 15 — consultas y reclamos                                 #
    # ------------------------------------------------------------------ #

    def file_claim(
        self,
        *,
        kind: str,
        record_id: str | None,
        subject_matter: str,
        body: str,
        filed_by: str,
        channel: str,
    ) -> Claim:
        """Radica una consulta o un reclamo y fija su vencimiento legal."""
        if kind not in {"query", "claim"}:
            raise DomainError(
                "El tipo debe ser 'query' (consulta, art. 14) o 'claim' (reclamo, art. 15)."
            )
        now = self._clock.now_ms()
        claim = Claim(
            id=self._ids.new_id("hd"),
            record_id=record_id,
            kind=kind,
            channel=channel,
            filed_by=filed_by,
            filed_at=now,
            due_at=deadline_for(kind, now, holidays=self._holidays),
            subject_matter=subject_matter,
            body=body,
        )
        self._claims.save(claim)
        return claim

    def extend_claim(self, claim_id: str, *, motive: str) -> Claim:
        """Prórroga del término. Solo vale si se informa al Titular con los motivos
        y antes de que venza el plazo inicial (art. 14 inc. 2 y art. 15 inc. final)."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise RecordNotFound(f"No existe la petición '{claim_id}'.")
        now = self._clock.now_ms()
        if now > claim.due_at:
            raise HabeasDataViolation(
                "El término ya venció: la prórroga debía informarse antes del "
                "vencimiento, con expresión de los motivos."
            )
        extended = replace(
            claim,
            status="extended",
            extended_until=extension_for(
                claim.kind, claim.due_at, holidays=self._holidays
            ),
            resolution=motive,
        )
        self._claims.save(extended)
        return extended

    def answer_claim(self, claim_id: str, *, resolution: str, accepted: bool) -> Claim:
        """Cierra la petición con respuesta de fondo."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise RecordNotFound(f"No existe la petición '{claim_id}'.")
        answered = replace(
            claim,
            status="answered" if accepted else "rejected",
            resolution=resolution,
            resolved_at=self._clock.now_ms(),
        )
        self._claims.save(answered)
        return answered

    def overdue_claims(self) -> list[Claim]:
        """Peticiones cuyo término ya venció. Alimenta la alarma operativa: que se
        venza un término es un incumplimiento, no un atraso."""
        now = self._clock.now_ms()
        return [
            c
            for c in self._claims.open_claims(now)
            if now > (c.extended_until or c.due_at)
        ]

    # ------------------------------------------------------------------ #
    # Art. 12 — deber de informar                                         #
    # ------------------------------------------------------------------ #

    def privacy_notice(self, controller: Controller) -> dict:
        """Aviso de privacidad (Decreto 1074 art. 2.2.2.25.3.2).

        Público y sin autenticación: es lo que se le debe poder mostrar a alguien
        cuyos datos se recogieron sin que estuviera en condiciones de leer nada.
        """
        return {
            "version": controller.privacy_notice_version,
            "responsable": {
                "nombre": controller.name,
                "identificacion": controller.legal_id,
                "contacto": controller.contact_email,
                "registro_rnbd": controller.rnbd_registration,
            },
            "finalidades": [
                "Reunificar a personas localizadas con su núcleo familiar.",
                "Coordinar la respuesta de los organismos de socorro del incidente.",
                "Notificar a las autoridades competentes cuando la ley lo exige.",
                "Producir estadística agregada que no identifica a ninguna persona.",
            ],
            "datos_sensibles": (
                "Este servicio puede tratar datos sensibles (ubicación en un centro "
                "asistencial, necesidades de atención, fotografía de reconocimiento). "
                "Usted no está obligado a autorizar su tratamiento. Cuando se traten "
                "sin su autorización será por interés vital estando usted incapacitado "
                "(art. 6 lit. b) o por urgencia sanitaria (art. 10 lit. c), y se le "
                "informará en cuanto sea posible."
            ),
            "derechos": [
                "Conocer, actualizar y rectificar sus datos.",
                "Solicitar prueba de la autorización otorgada.",
                "Ser informado sobre el uso que se ha dado a sus datos.",
                "Presentar quejas ante la Superintendencia de Industria y Comercio.",
                "Revocar la autorización y solicitar la supresión del dato.",
                "Acceder de forma gratuita a sus datos personales.",
            ],
            "canal_de_ejercicio": (
                f"Escriba a {controller.contact_email} o radique su petición en "
                "POST /v1/habeas-data/peticiones. Consultas: 10 días hábiles. "
                "Reclamos: 15 días hábiles."
            ),
            "retencion": (
                "Los datos operativos se conservan 30 días después del cierre del "
                "incidente y luego se anonimizan de forma irreversible."
            ),
            "base_normativa": [
                "Constitución Política, artículo 15",
                "Ley 1581 de 2012",
                "Decreto 1074 de 2015 (que compila el Decreto 1377 de 2013)",
            ],
        }

    # ------------------------------------------------------------------ #
    # Interno                                                             #
    # ------------------------------------------------------------------ #

    def _require(self, record_id: str) -> FoundPersonRecord:
        record = self._repo.get(record_id)
        if record is None:
            raise RecordNotFound(f"No existe el registro '{record_id}'.")
        if record.lifecycle is RecordLifecycle.ANONYMIZED:
            raise HabeasDataViolation(
                "El registro fue anonimizado al vencer la retención; ya no hay datos "
                "personales sobre los que ejercer derechos."
            )
        return record

    def _emit_tombstone(
        self, record: FoundPersonRecord, *, reason: TombstoneReason, now_ms: int
    ) -> None:
        tombstone = Tombstone(
            record_id=record.id,
            incident_id=record.incident_id,
            issued_at=now_ms,
            reason=reason,
            sequence=self._tombstones.next_sequence(record.incident_id),
        )
        self._tombstones.append(
            replace(
                tombstone,
                signature=self._signer.sign(
                    canonical_bytes(
                        {
                            "typ": "found_persons.tombstone.v1",
                            "record_id": tombstone.record_id,
                            "incident_id": tombstone.incident_id,
                            "issued_at": tombstone.issued_at,
                            "reason": tombstone.reason.value,
                            "sequence": tombstone.sequence,
                        }
                    )
                ),
            )
        )


__all__ = [
    "BASIS_EXPLANATIONS",
    "ConsentProofView",
    "DataSubjectRightsService",
    "DisclosureScope",
    "Purpose",
]
