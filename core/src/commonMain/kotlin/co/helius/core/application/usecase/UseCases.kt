package co.helius.core.application.usecase

import co.helius.core.application.ports.*
import co.helius.core.domain.vo.PeerId
import co.helius.core.domain.vo.PeerLink
import co.helius.core.signal.motion.ActivityEvidenceClassifier
import co.helius.core.signal.motion.DeterministicActivityClassifier
import co.helius.core.signal.motion.MotionClassification
import kotlinx.coroutines.flow.first

/**
 * Casos de uso de orquestación (Sección 4.1: "APPLICATION — casos de uso / orquestación").
 * Cada uno depende SOLO de puertos (application/ports), nunca de adaptadores concretos.
 * Un archivo por caso de uso en producción — agrupados aquí como placeholder de scaffold.
 */

/** Activación de emergencia: fuente sísmica → CAP → decisión → notificación → cambio de modo. Dueño: Miguel (alert_ingestor) + Helmut (cambio de modo). */
class ActivateEmergency(private val powerPolicy: PowerPolicyPort, private val alerts: AlertReceiverPort) {
    suspend operator fun invoke() { TODO("dueño=Helmut/Miguel") }
}

/** Registra la respuesta explícita del usuario (SAFE/NEEDS_HELP/TRAPPED). Dueño: Laura. */
class RecordUserResponse(private val store: BundleStorePort, private val identity: IdentityPort) {
    suspend operator fun invoke(state: Any) { TODO("dueño=Laura") }
}

/**
 * Orquesta un encuentro DTN completo con un peer. Para el adaptador BLE,
 * `TransportPort.connect()` ya incluye la sincronización completa de
 * inventario/bundles (ver android/transport/BleTransport.kt +
 * BleGattClient.kt) — por eso este caso de uso es solo un paso-a-través hoy.
 * Si un transporte futuro (Wi-Fi Aware, UWB) NO hace la sincronización
 * dentro de `connect()`, este caso de uso es el lugar para invocar
 * `EncounterStateMachine.exchange()` explícitamente contra el store local y
 * uno remoto expuesto por ese transporte. Dueño: Helmut.
 */
class ExchangeWithPeer(private val transport: TransportPort) {
    suspend operator fun invoke(peer: PeerId): PeerLink = transport.connect(peer)
}

/**
 * Evalúa evidencia de actividad/movimiento intencional a partir de la
 * ventana más reciente de [MotionPort] (acelerómetro + giroscopio). Dueño:
 * Alex. Clasificador determinista por defecto -- ver
 * core/signal/motion/ActivityEvidenceClassifier.kt.
 */
class EvaluateActivityEvidence(
    private val motion: MotionPort,
    private val classifier: ActivityEvidenceClassifier = DeterministicActivityClassifier(),
) {
    suspend operator fun invoke(): MotionClassification = classifier.classify(motion.observeMotionWindows().first())
}

/** Corre una sesión de captura + inferencia AIB (pulso, SQI). Dueño: Laura (captura) + Alex (inferencia). */
class RunBiomarkerSession(private val ppg: PpgCapturePort, private val inference: BiomarkerInferencePort) {
    suspend operator fun invoke() { TODO("dueño=Laura/Alex — frontera contractual: BiomarkerInferencePort") }
}

/** Sube al backend cuando hay conectividad. Dueño: Miguel. */
class SyncGateway(private val cloud: CloudSyncPort) {
    suspend operator fun invoke() { TODO("dueño=Miguel") }
}

/**
 * Transición READY/ALERT/TRAPPED/RESCUER (Sección 7.3-7.4). Delega la
 * decisión de "cómo" (advertising/scan/foreground service) al adaptador real
 * (`:android:power`, aún sin implementar) — este caso de uso solo valida que
 * el modo pedido tenga sentido dado el estado actual antes de pedir la
 * transición. Nunca se pasa de `RESCUER` a `READY` directamente (debe pasar
 * por una desactivación explícita del incidente, no por este caso de uso).
 * Dueño: Helmut.
 */
class EnterPowerMode(private val powerPolicy: PowerPolicyPort) {
    suspend operator fun invoke(mode: PowerMode) {
        val current = powerPolicy.currentMode()
        require(!(current == PowerMode.RESCUER && mode == PowerMode.READY)) {
            "No se permite RESCUER -> READY directo; requiere desactivación explícita del incidente"
        }
        powerPolicy.enterMode(mode)
    }
}
