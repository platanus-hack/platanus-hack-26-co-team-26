package co.sismomesh.core.domain.policy

/** Políticas del dominio — puras, sin efectos secundarios, 100% testeables en JVM. */

/** score de reenvío, ver core/dtn/ForwardingScorer.kt. Dueño: Helmut. */
class ForwardingPolicy

/** cuota por tier, expiración, LRU ponderado. Dueño: Helmut. */
class RetentionPolicy

/** modos READY/ALERT/TRAPPED/RESCUER y su ciclo de trabajo (Sección 7.4-7.5). Dueño: Helmut. */
class PowerPolicy

/**
 * Combina reporte del usuario + evidencia de movimiento + evidencia de pulso + confianza
 * de ubicación + antigüedad → nivel de atención (ALTO/MEDIO/BAJO/SIN EVIDENCIA).
 * NUNCA "triage médico" — ver Anexo B, vocabulario obligatorio. Dueño: Alex.
 */
class AttentionLevelPolicy {
    fun evaluate(input: AttentionInput): AttentionLevel = TODO("dueño=Alex, Sección 11.6")
}

data class AttentionInput(
    val userReport: Any?,
    val motionEvidence: Any?,
    val biomarkerEvidence: Any?,
    val locationConfidence: Double?,
    val evidenceAgeMs: Long,
)

enum class AttentionLevel { ALTO, MEDIO, BAJO, SIN_EVIDENCIA }
