import kotlin.test.Ignore
import kotlin.test.Test

/**
 * Escenario A→B→C→R de la Sección 8.1: Ana(A) —status→ Juan(B) —A+B→ Paula(C)
 * —A+B+C→ Rescatista(R) → Cloud. Corre 100% en JVM con LoopbackFake, sin ningún
 * teléfono. Marcado @Ignore hasta que core/dtn tenga implementación real —
 * debe compilar desde el día 1 (Anexo A, punto 10).
 */
class DtnEncounterScenarioTest {
    @Ignore
    @Test
    fun `A alcanza a R via B y C via store-carry-forward`() {
        TODO("dueño=Helmut — usar LoopbackFake de TransportPort")
    }
}
