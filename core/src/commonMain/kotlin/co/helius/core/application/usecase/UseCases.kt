package co.helius.core.application.usecase

import co.helius.core.application.ports.*
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

/** Orquesta un encuentro DTN completo con un peer. Dueño: Helmut. */
class ExchangeWithPeer(private val transport: TransportPort, private val store: BundleStorePort) {
    suspend operator fun invoke(peer: Any) { TODO("dueño=Helmut") }
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
class RunBiomarkerSession(private val ppg: PpgCaptureIPort, private val inference: BiomarkerInferencePort) {
    suspend operator fun invoke() { TODO("dueño=Laura/Alex — frontera contractual: BiomarkerInferencePort") }
}

/** Sube al backend cuando hay conectividad. Dueño: Miguel. */
class SyncGateway(private val cloud: CloudSyncPort) {
    suspend operator fun invoke() { TODO("dueño=Miguel") }
}

/** Transición READY/ALERT/TRAPPED/RESCUER (Sección 7.3-7.4). Dueño: Helmut. */
class EnterPowerMode(private val powerPolicy: PowerPolicyPort) {
    suspend operator fun invoke(mode: Any) { TODO("dueño=Helmut") }
}
