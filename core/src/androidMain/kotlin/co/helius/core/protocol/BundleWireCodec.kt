package co.helius.core.protocol

import co.helius.core.domain.model.Bundle as DomainBundle
import co.helius.core.domain.model.BundleHeader as DomainBundleHeader
import co.helius.core.domain.model.BundlePayload
import co.helius.core.domain.model.ClockEvidence as DomainClockEvidence
import co.helius.core.domain.model.EmergencyStatus as DomainEmergencyStatus
import co.helius.core.domain.model.PeerObservation as DomainPeerObservation
import co.helius.core.domain.model.ResponseState as DomainResponseState
import co.helius.core.domain.vo.AltitudeSource as DomainAltitudeSource
import co.helius.core.domain.vo.Battery
import co.helius.core.domain.vo.BundleId
import co.helius.core.domain.vo.GeoPoint as DomainGeoPoint
import co.helius.core.domain.vo.NodeId
import co.helius.core.domain.vo.Priority as DomainPriority
import co.helius.core.protocol.v1.AltitudeSource as WireAltitudeSource
import co.helius.core.protocol.v1.Bundle as WireBundle
import co.helius.core.protocol.v1.BundleHeader as WireBundleHeader
import co.helius.core.protocol.v1.ClockEvidence as WireClockEvidence
import co.helius.core.protocol.v1.EmergencyStatus as WireEmergencyStatus
import co.helius.core.protocol.v1.GeoPoint as WireGeoPoint
import co.helius.core.protocol.v1.PeerObservation as WirePeerObservation
import co.helius.core.protocol.v1.Priority as WirePriority
import co.helius.core.protocol.v1.ResponseState as WireResponseState
import com.google.protobuf.ByteString

/**
 * Puente entre el modelo de dominio (`core/domain/model`, puro, sin protobuf)
 * y el formato de wire generado (`core/protocol/v1`, protobuf). Sin este
 * puente, un `Bundle` de dominio nunca puede convertirse en bytes reales para
 * transmitirse por ningún transporte — es la pieza que faltaba para que
 * `BleGattClient`/`BleGattServer` muevan datos de verdad.
 *
 * **Cobertura actual:** `Status` (evidencia de emergencia, necesario para el
 * Slice 0 — docs/roadmap/VERTICAL-SLICES.md), `Observation` (`PeerObservation`,
 * alimenta la localización probabilística), `Raw` y `Responder` (ambos solo
 * bytes). `Motion`/`Biomarker` siguen siendo `Any` de relleno en
 * `core/domain/model/Bundle.kt` (TODO de Alex) — hasta que tengan un tipo
 * real, `toWire()`/`fromWire()` lanzan `NotImplementedError` en vez de fingir
 * que funcionan.
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
                co.helius.core.protocol.v1.RawSensorChunk.newBuilder()
                    .setChunk(ByteString.copyFrom(p.chunk))
                    .build(),
            )
            is BundlePayload.Responder -> builder.setResponder(
                co.helius.core.protocol.v1.ResponderMessage.newBuilder()
                    .setCiphertext(ByteString.copyFrom(p.message))
                    .build(),
            )
            is BundlePayload.Motion -> throw NotImplementedError(
                "BundleWireCodec: MotionEvidence real pendiente (dueño=Alex) — ver core/domain/model/Bundle.kt",
            )
            is BundlePayload.Biomarker -> throw NotImplementedError(
                "BundleWireCodec: BiomarkerEvidence real pendiente (dueño=Alex) — ver core/domain/model/Bundle.kt",
            )
            is BundlePayload.Observation -> builder.setObservation(p.peerObservation.toWireMessage())
        }
        return builder.build()
    }

    private fun WireBundle.toDomain(): DomainBundle {
        val payload: BundlePayload = when (payloadCase) {
            WireBundle.PayloadCase.STATUS -> BundlePayload.Status(status.toDomain())
            WireBundle.PayloadCase.RAW -> BundlePayload.Raw(raw.chunk.toByteArray())
            WireBundle.PayloadCase.RESPONDER -> BundlePayload.Responder(responder.ciphertext.toByteArray())
            WireBundle.PayloadCase.OBSERVATION -> BundlePayload.Observation(observation.toDomain())
            WireBundle.PayloadCase.MOTION, WireBundle.PayloadCase.BIOMARKER ->
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
            .setPriority(priority.toWirePriority())
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

    private fun DomainEmergencyStatus.toWireMessage(): WireEmergencyStatus {
        val domainLocation = location
        return WireEmergencyStatus.newBuilder()
            .apply { domainLocation?.let { setLocation(it.toWireGeoPointMessage()) } }
            .setTs(timestampMs.toLong())
            .setSource(source)
            .setResponseState(responseState.toWireResponseState())
            .setBattery(battery.percent)
            .setDeviceState(deviceState)
            .addAllEvidenceRefs(evidenceRefs)
            .build()
    }

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

    private fun DomainGeoPoint.toWireGeoPointMessage(): WireGeoPoint {
        val domainAltitudeSource = altitudeSource
        return WireGeoPoint.newBuilder()
            .setLat(lat)
            .setLon(lon)
            .apply {
                accuracyM?.let { setAccM(it) }
                altitudeM?.let { setAltitudeM(it) }
                altitudeAccuracyM?.let { setAltitudeAccM(it) }
                if (domainAltitudeSource != DomainAltitudeSource.UNKNOWN) setAltitudeSource(domainAltitudeSource.toWireAltitudeSource())
            }
            .build()
    }

    private fun WireGeoPoint.toDomain(): DomainGeoPoint =
        DomainGeoPoint(
            lat = lat,
            lon = lon,
            accuracyM = if (hasAccM()) accM else null,
            altitudeM = if (hasAltitudeM()) altitudeM else null,
            altitudeAccuracyM = if (hasAltitudeAccM()) altitudeAccM else null,
            altitudeSource = if (hasAltitudeSource()) altitudeSource.toDomain() else DomainAltitudeSource.UNKNOWN,
        )

    private fun DomainAltitudeSource.toWireAltitudeSource(): WireAltitudeSource = WireAltitudeSource.forNumber(ordinal)
        ?: error("AltitudeSource sin mapeo wire: $this")

    private fun WireAltitudeSource.toDomain(): DomainAltitudeSource = DomainAltitudeSource.entries[number]

    private fun DomainPriority.toWirePriority(): WirePriority = WirePriority.forNumber(ordinal)
        ?: error("Priority sin mapeo wire: $this")

    private fun WirePriority.toDomain(): DomainPriority = DomainPriority.entries[number]

    private fun DomainResponseState.toWireResponseState(): WireResponseState = WireResponseState.forNumber(ordinal)
        ?: error("ResponseState sin mapeo wire: $this")

    private fun WireResponseState.toDomain(): DomainResponseState = DomainResponseState.entries[number]

    private fun DomainPeerObservation.toWireMessage(): WirePeerObservation =
        WirePeerObservation.newBuilder()
            .setIncidentId(ByteString.copyFrom(incidentId))
            .setNodeA(ByteString.copyFromUtf8(nodeA.value))
            .setNodeB(ByteString.copyFromUtf8(nodeB.value))
            .setRssiDbm(rssiDbm)
            .setTransport(transport)
            .setObservedAt(observedAtMs.toLong())
            .apply {
                observerGeo?.let { setObserverGeo(it.toWireMessage()) }
                observerAccM?.let { setObserverAccM(it) }
                uwbElevationDeg?.let { setUwbElevationDeg(it) }
                uwbAzimuthDeg?.let { setUwbAzimuthDeg(it) }
                uwbDistanceM?.let { setUwbDistanceM(it) }
                barometricPressureHpa?.let { setBarometricPressureHpa(it) }
            }
            .build()

    private fun WirePeerObservation.toDomain(): DomainPeerObservation =
        DomainPeerObservation(
            incidentId = incidentId.toByteArray(),
            nodeA = NodeId(nodeA.toStringUtf8()),
            nodeB = NodeId(nodeB.toStringUtf8()),
            rssiDbm = rssiDbm,
            transport = transport,
            observedAtMs = observedAt.toULong(),
            observerGeo = if (hasObserverGeo()) observerGeo.toDomain() else null,
            observerAccM = if (hasObserverAccM()) observerAccM else null,
            uwbElevationDeg = if (hasUwbElevationDeg()) uwbElevationDeg else null,
            uwbAzimuthDeg = if (hasUwbAzimuthDeg()) uwbAzimuthDeg else null,
            uwbDistanceM = if (hasUwbDistanceM()) uwbDistanceM else null,
            barometricPressureHpa = if (hasBarometricPressureHpa()) barometricPressureHpa else null,
        )
}
