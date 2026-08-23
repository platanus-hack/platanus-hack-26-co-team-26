package co.helius.core.application.ports

/**
 * Retroalimentación auditiva de proximidad para el teléfono del rescatista —
 * beep tipo detector de metales cuya cadencia depende del RSSI del peer más
 * cercano, más una alerta única cuando aparece un peer nuevo en rango de
 * escaneo. Nunca voz ni audio pregenerado: la distancia cambia en vivo, ver
 * `co.helius.core.domain.proximity.ProximityAudioMapper`.
 *
 * Dueño: Helmut. Adaptador real: `ToneGenerator`/oscilador en Android
 * (pendiente, requiere dispositivo — ver docs/validation/PHONE-READINESS.md).
 */
interface ProximityAudioPort {
    /** Empieza a sonar (o retimbra si ya estaba sonando) al ritmo dado. */
    suspend fun startBeeping(intervalMs: Long)

    /** Ajusta el ritmo del beep en curso, sin cortarlo. */
    suspend fun updateInterval(intervalMs: Long)

    /** Detiene el beep (peer fuera de rango, o pantalla de proximidad cerrada). */
    suspend fun stopBeeping()

    /** Tono único, distinto del beep de proximidad: "apareció un peer nuevo". */
    suspend fun playPeerDetectedChime()
}
