package co.helius.core.domain.proximity

import co.helius.core.domain.vo.PeerId

/**
 * Mapea RSSI de un [co.helius.core.domain.vo.PeerSighting] a un ritmo de
 * "beep" para el teléfono del rescatista — el equivalente auditivo de un
 * detector de metales: más cerca, beep más rápido. Deliberadamente NO usa
 * ElevenLabs ni ningún audio pregenerado: la distancia cambia en vivo
 * mientras el rescatista camina, así que no hay forma de pre-grabar "más
 * rápido a medida que te acercas" — tiene que sintetizarse en el momento
 * (`ToneGenerator`/oscilador en el adaptador Android, pendiente, requiere
 * dispositivo). Ver docs/voice/VOICE-GUIDANCE.md § Proximidad.
 *
 * Rango típico de RSSI en BLE de corto alcance: -30 dBm (pegado al peer) a
 * -100 dBm (borde del rango de escaneo). Los umbrales de aquí son
 * ingeniería de producto, no una medición calibrada de distancia real —
 * RSSI no es distancia (ver docs/glossary.md, restricción no negociable 7).
 */
object ProximityAudioMapper {
    private const val NEAR_DBM = -40
    private const val FAR_DBM = -95
    private const val MIN_INTERVAL_MS = 120L
    private const val MAX_INTERVAL_MS = 1_500L

    /** dBm a partir del cual se considera "rango operativo": lo bastante cerca
     * para que valga la pena buscar visualmente en vez de seguir caminando. */
    const val OPERATIVE_RANGE_DBM = -55

    /**
     * Intervalo entre beeps en milisegundos. Nunca fuera de
     * [MIN_INTERVAL_MS, MAX_INTERVAL_MS] — un RSSI más fuerte que NEAR_DBM no
     * acelera más el beep (el oído no distingue diferencias por debajo de
     * MIN_INTERVAL_MS de todos modos), y uno más débil que FAR_DBM no lo
     * hace más lento (fuera de rango es silencio, no un beep casi imperceptible).
     */
    fun beepIntervalMs(rssiDbm: Int): Long {
        val clamped = rssiDbm.coerceIn(FAR_DBM, NEAR_DBM)
        val fraction = (clamped - FAR_DBM).toDouble() / (NEAR_DBM - FAR_DBM) // 0 lejos .. 1 cerca
        return (MAX_INTERVAL_MS - fraction * (MAX_INTERVAL_MS - MIN_INTERVAL_MS)).toLong()
    }

    /** true si el peer está lo bastante cerca como para justificar buscar visualmente. */
    fun isOperativeRange(rssiDbm: Int): Boolean = rssiDbm >= OPERATIVE_RANGE_DBM
}

/** Una de las dos señales auditivas que puede producir un avistamiento. */
sealed interface ProximityAlert {
    /** Ritmo de beep a mantener mientras este peer siga siendo el más cercano. */
    data class Beep(val intervalMs: Long) : ProximityAlert

    /** Tono único: este peer nunca se había visto en esta sesión de búsqueda. */
    data object NewPeerChime : ProximityAlert
}

/**
 * Reduce avistamientos (`PeerSighting`, vía `TransportPort.observePeers()`) a
 * alertas auditivas. Con estado mínimo (qué peers ya sonaron su chime en esta
 * sesión) para no repetir el aviso de "nuevo peer" cada vez que llega otro
 * beacon del mismo dispositivo — un peer BLE anuncia cada pocos segundos
 * mientras esté en rango, no una sola vez.
 */
class ProximityAlertReducer {
    private val chimedPeerIds = mutableSetOf<PeerId>()

    /** Alertas a disparar para este avistamiento, en orden: como mucho un
     * [ProximityAlert.NewPeerChime] (solo la primera vez que se ve este peer
     * en la sesión) seguido siempre de un [ProximityAlert.Beep]. */
    fun onSighting(peerId: PeerId, rssiDbm: Int): List<ProximityAlert> {
        val alerts = mutableListOf<ProximityAlert>()
        if (chimedPeerIds.add(peerId)) alerts += ProximityAlert.NewPeerChime
        alerts += ProximityAlert.Beep(ProximityAudioMapper.beepIntervalMs(rssiDbm))
        return alerts
    }

    /** Limpia el historial de peers ya avisados — llamar al empezar una nueva
     * búsqueda (p. ej. el rescatista sale a un área distinta). */
    fun reset() = chimedPeerIds.clear()
}
