import co.sismomesh.core.domain.model.Bundle
import co.sismomesh.core.domain.model.BundleHeader
import co.sismomesh.core.domain.model.BundlePayload
import co.sismomesh.core.domain.model.ClockEvidence
import co.sismomesh.core.domain.model.EmergencyStatus
import co.sismomesh.core.domain.model.ResponseState
import co.sismomesh.core.domain.vo.Battery
import co.sismomesh.core.domain.vo.BundleId
import co.sismomesh.core.domain.vo.NodeId
import co.sismomesh.core.domain.vo.Priority
import co.sismomesh.core.dtn.EncounterStateMachine
import co.sismomesh.core.dtn.InMemoryBundleStore
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Escenario A→B→C→R de la Sección 8.1: Ana(A) —status→ Juan(B) —A+B→ Paula(C)
 * —A+B+C→ Rescatista(R) → Cloud. Corre 100% en JVM con InMemoryBundleStore,
 * sin ningún teléfono (ADR-0001). Criterio de aceptación del Slice 0.
 */
class DtnEncounterScenarioTest {

    private fun statusBundle(nodeLabel: String, seq: Long): Bundle {
        val header = BundleHeader(
            version = 1,
            disasterId = "sismo-2026-08-22",
            bundleId = BundleId("bundle-$nodeLabel-$seq".encodeToByteArray()),
            nodeId = NodeId("node-$nodeLabel"),
            sequence = seq.toULong(),
            createdAtMs = 1_755_878_400_000UL,
            expiresAtMs = 1_755_882_000_000UL,
            hopCount = 0,
            priority = Priority.P1_LOCATION,
            clockEvidence = ClockEvidence(monotonicMs = 0, observedSkewMs = null),
        )
        val status = EmergencyStatus(
            location = null,
            timestampMs = 1_755_878_400_000L,
            source = "gnss",
            responseState = ResponseState.NEEDS_HELP,
            battery = Battery(percent = 50),
            deviceState = "foreground_service",
        )
        return Bundle(header, BundlePayload.Status(status), signature = ByteArray(0))
    }

    @Test
    fun `A alcanza a R via B y C por store-carry-forward`() = runTest {
        val storeA = InMemoryBundleStore()
        val storeB = InMemoryBundleStore()
        val storeC = InMemoryBundleStore()
        val storeR = InMemoryBundleStore()
        val encounter = EncounterStateMachine()

        val bundleFromA = statusBundle("A", seq = 1)
        storeA.save(bundleFromA)

        // A nunca alcanza a R directamente en este escenario.
        assertFalse(storeR.contains(bundleFromA.header.bundleId))

        // Encuentro 1: A <-> B
        encounter.exchange(storeA, storeB)
        assertTrue(storeB.contains(bundleFromA.header.bundleId), "B debería tener el bundle de A tras el encuentro")

        // B se desplaza y encuentra a C: comparte lo que ya trae (incluido A+B).
        val bundleFromB = statusBundle("B", seq = 1)
        storeB.save(bundleFromB)
        encounter.exchange(storeB, storeC)
        assertTrue(storeC.contains(bundleFromA.header.bundleId))
        assertTrue(storeC.contains(bundleFromB.header.bundleId))

        // C encuentra al rescatista R: comparte A+B+C.
        val bundleFromC = statusBundle("C", seq = 1)
        storeC.save(bundleFromC)
        encounter.exchange(storeC, storeR)

        assertTrue(storeR.contains(bundleFromA.header.bundleId), "R debe recibir la evidencia de A vía store-carry-forward")
        assertTrue(storeR.contains(bundleFromB.header.bundleId))
        assertTrue(storeR.contains(bundleFromC.header.bundleId))
        assertEquals(3, storeR.all().size)
    }

    @Test
    fun `el intercambio de inventarios no duplica bundles ya conocidos`() = runTest {
        val storeA = InMemoryBundleStore()
        val storeB = InMemoryBundleStore()
        val encounter = EncounterStateMachine()

        val bundle = statusBundle("A", seq = 1)
        storeA.save(bundle)
        storeB.save(bundle) // B ya lo tiene (p. ej. de un encuentro anterior)

        encounter.exchange(storeA, storeB)

        assertEquals(1, storeB.all().size, "no debe duplicarse un bundle que el peer ya tenía")
    }
}
