package co.sismomesh.core.protocol

import co.sismomesh.core.domain.model.Bundle as DomainBundle
import co.sismomesh.core.domain.model.BundleHeader as DomainBundleHeader
import co.sismomesh.core.domain.model.BundlePayload
import co.sismomesh.core.domain.model.ClockEvidence as DomainClockEvidence
import co.sismomesh.core.domain.model.EmergencyStatus as DomainEmergencyStatus
import co.sismomesh.core.domain.model.ResponseState as DomainResponseState
import co.sismomesh.core.domain.vo.AltitudeSource as DomainAltitudeSource
import co.sismomesh.core.domain.vo.Battery
import co.sismomesh.core.domain.vo.BundleId
import co.sismomesh.core.domain.vo.GeoPoint as DomainGeoPoint
import co.sismomesh.core.domain.vo.NodeId
import co.sismomesh.core.domain.vo.Priority as DomainPriority
import co.sismomesh.core.protocol.v1.AltitudeSource as WireAltitudeSource
import co.sismomesh.core.protocol.v1.Bundle as WireBundle
import co.sismomesh.core.protocol.v1.BundleHeader as WireBundleHeader
import co.sismomesh.core.protocol.v1.ClockEvidence as WireClockEvidence
import co.sismomesh.core.protocol.v1.EmergencyStatus as WireEmergencyStatus
import co.sismomesh.core.protocol.v1.GeoPoint as WireGeoPoint
import co.sismomesh.core.protocol.v1.Priority as WirePriority
import co.sismomesh.core.protocol.v1.ResponseState as WireResponseState
import com.google.protobuf.ByteString

/**
 * Puente entre el modelo de dominio (`core/domain/model`, puro, sin protobuf)
 * y el formato de wire generado (`core/protocol/v1`, protobuf). Sin este
 * puente, un `Bundle` de dominio nunca puede convertirse en bytes reales para
 * transmitirse por ningún transporte — es la pieza que faltaba para que
 * `BleGattClient`/`BleGattServer` muevan datos de verdad.
 *
 * **Cobertura actual: solo el payload `Status`** (evidencia de emergencia) —
 * es el que necesita el Slice 0 ("NECESITO AYUDA" A→B→C→R,
 * docs/roadmap/VERTICAL-SLICES.md). `Motion`/`Biomarker`/`Observation` en
 * `core/domain/model/Bundle.kt` siguen siendo `Any` de relleno (TODO de
 * Alex/Helmut) — hasta que tengan un tipo real, `toWire()`/`fromWire()`
 * lanzan `NotImplementedError` para esos casos en vez de fingir que
 * funcionan. `Raw` sí está cubierto (es solo bytes).
 *
 * Dueño: Helmut. Revisor obligatorio: Alex (cuando defina MotionEvidence/BiomarkerEvidence reales).
 */
object BundleWireCodec {

    fun DomainBundle.toWire(): ByteArray = toWireMessage().toByteArray()

    fun ByteArray.toDomainBundle(): DomainBundle = WireBundle.parseFrom(this).toDomain()

    private fun DomainBundle.toWireMessage(): WireBundle {
        val builder = WireBundle.newBuilder()
            .setHeader(header.toWireMessage())
            .setSignature(ByteString.copyFrom(signature))

        when (val p = payload) {
            is BundlePayload.Status -> builder.setStatus(p.evidence.toWireMessage())
            is BundlePayload.Raw -> builder.setRaw(
                co.sismomesh.core.protocol.v1.RawSensorChunk.newBuilder()
                    .setChunk(ByteString.copyFrom(p.chunk))
                    .build(),
            )
            is BundlePayload.Responder -> builder.setResponder(
                co.sismomesh.core.protocol.v1.ResponderMessage.newBuilder()
                    .setCiphertext(ByteString.copyFrom(p.message))
                    .build(),
            )
            is BundlePayload.Motion -> throw NotImplementedError(
                "BundleWireCodec: MotionEvidence real pendiente (dueño=Alex) — ver core/domain/model/Bundle.kt",
            )
            is BundlePayload.Biomarker -> throw NotImplementedError(
                "BundleWireCodec: BiomarkerEvidence real pendiente (dueño=Alex) — ver core/domain/model/Bundle.kt",
            )
            is BundlePayload.Observation -> throw NotImplementedError(
                "BundleWireCodec: PeerObservation real pendiente (dueño=Helmut) — ver core/domain/model/Bundle.kt",
            )
        }
        return builder.build()
    }

    private fun WireBundle.toDomain(): DomainBundle {
        val payload: BundlePayload = when (payloadCase) {
            WireBundle.PayloadCase.STATUS -> BundlePayload.Status(status.toDomain())
            WireBundle.PayloadCase.RAW -> BundlePayload.Raw(raw.chunk.toByteArray())
            WireBundle.PayloadCase.RESPONDER -> BundlePayload.Responder(responder.ciphertext.toByteArray())
            WireBundle.PayloadCase.MOTION, WireBundle.PayloadCase.BIOMARKER, WireBundle.PayloadCase.OBSERVATION ->
                throw NotImplementedError("BundleWireCodec: payload '$payloadCase' aún no tiene tipo de dominio real")
            WireBundle.PayloadCase.PAYLOAD_NOT_SET, null ->
                throw IllegalArgumentException("Bundle recibido sin payload")
        }
        return DomainBundle(header.toDomain(), payload, signature.toByteArray())
    }

    private fun DomainBundleHeader.toWireMessage(): WireBundleHeader =
        WireBundleHeader.newBuilder()
            .setVersion(version)
            .setDisasterId(disasterId)
            .setBundleId(ByteString.copyFrom(bundleId.bytes))
            .setNodeId(ByteString.copyFromUtf8(nodeId.value))
            .setSequence(sequence.toLong())
            .setCreatedAt(createdAtMs.toLong())
            .setExpiresAt(expiresAtMs.toLong())
            .setHopCount(hopCount)
            .setPriority(priority.toWire())
            .setClock(clockEvidence.toWireMessage())
            .build()

    private fun WireBundleHeader.toDomain(): DomainBundleHeader =
        DomainBundleHeader(
            version = version,
            disasterId = disasterId,
            bundleId = BundleId(bundleId.toByteArray()),
            nodeId = NodeId(nodeId.toStringUtf8()),
            sequence = sequence.toULong(),
            createdAtMs = createdAt.toULong(),
            expiresAtMs = expiresAt.toULong(),
            hopCount = hopCount,
            priority = priority.toDomain(),
            clockEvidence = clock.toDomain(),
        )

    private fun DomainClockEvidence.toWireMessage(): WireClockEvidence =
        WireClockEvidence.newBuilder()
            .setMonotonicMs(monotonicMs)
            .apply { observedSkewMs?.let { setObservedSkewMs(it) } }
            .build()

    private fun WireClockEvidence.toDomain(): DomainClockEvidence =
        DomainClockEvidence(monotonicMs = monotonicMs, observedSkewMs = if (hasObservedSkewMs()) observedSkewMs else null)

    private fun DomainEmergencyStatus.toWireMessage(): WireEmergencyStatus =
        WireEmergencyStatus.newBuilder()
            .apply { location?.let { setLocation(it.toWireMessage()) } }
            .setTs(timestampMs.toLong())
            .setSource(source)
            .setResponseState(responseState.toWire())
            .setBattery(battery.percent)
            .setDeviceState(deviceState)
            .addAllEvidenceRefs(evidenceRefs)
            .build()

    private fun WireEmergencyStatus.toDomain(): DomainEmergencyStatus =
        DomainEmergencyStatus(
            location = if (hasLocation()) location.toDomain() else null,
            timestampMs = ts,
            source = source,
            responseState = responseState.toDomain(),
            battery = Battery(battery),
            deviceState = deviceState,
            evidenceRefs = evidenceRefsList,
        )

    private fun DomainGeoPoint.toWireMessage(): WireGeoPoint =
        WireGeoPoint.newBuilder()
            .setLat(lat)
            .setLon(lon)
            .apply {
                accuracyM?.let { setAccM(it) }
                altitudeM?.let { setAltitudeM(it) }
                altitudeAccuracyM?.let { setAltitudeAccM(it) }
                if (altitudeSource != DomainAltitudeSource.UNKNOWN) setAltitudeSource(altitudeSource.toWire())
            }
            .build()

    private fun WireGeoPoint.toDomain(): DomainGeoPoint =
        DomainGeoPoint(
            lat = lat,
            lon = lon,
            accuracyM = if (hasAccM()) accM else null,
            altitudeM = if (hasAltitudeM()) altitudeM else null,
            altitudeAccuracyM = if (hasAltitudeAccM()) altitudeAccM else null,
            altitudeSource = if (hasAltitudeSource()) altitudeSource.toDomain() else DomainAltitudeSource.UNKNOWN,
        )

    private fun DomainAltitudeSource.toWire(): WireAltitudeSource = WireAltitudeSource.forNumber(ordinal)
        ?: error("AltitudeSource sin mapeo wire: $this")

    private fun WireAltitudeSource.toDomain(): DomainAltitudeSource = DomainAltitudeSource.entries[number]

    private fun DomainPriority.toWire(): WirePriority = WirePriority.forNumber(ordinal)
        ?: error("Priority sin mapeo wire: $this")

    private fun WirePriority.toDomain(): DomainPriority = DomainPriority.entries[number]

    private fun DomainResponseState.toWire(): WireResponseState = WireResponseState.forNumber(ordinal)
        ?: error("ResponseState sin mapeo wire: $this")

    private fun WireResponseState.toDomain(): DomainResponseState = DomainResponseState.entries[number]
}
