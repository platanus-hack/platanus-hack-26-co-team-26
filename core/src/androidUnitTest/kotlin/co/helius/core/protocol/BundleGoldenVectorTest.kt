package co.helius.core.protocol

import co.helius.core.protocol.BundleWireCodec.toDomainBundle
import co.helius.core.protocol.BundleWireCodec.toWire
import java.io.File
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertTrue

/**
 * Round-trip Kotlin real contra los vectores dorados de
 * `protocol/test-vectors/bundles/` — la mitad Kotlin del contrato
 * "protocol-ci.yml", que hasta ahora solo tenía la verificación Python
 * (`protocol/test-vectors/verify_python_roundtrip.py`). Corre en la JVM
 * local (androidUnitTest), sin ningún teléfono.
 *
 * Cobertura: `status_trapped`, `observation_peer`, `raw_chunk` — los tres
 * tipos de payload que `BundleWireCodec` ya soporta. `motion_purposeful` y
 * `biomarker_pulse` quedan fuera hasta que Alex defina `MotionEvidence`/
 * `BiomarkerEvidence` reales (ver `BundleWireCodec`, `NotImplementedError`
 * explícito para esos dos casos).
 *
 * Ruta relativa: los tests de Gradle para un módulo corren con el
 * directorio del módulo (`core/`) como working directory, por eso
 * `../protocol/...` resuelve a la raíz del repo. Si esto falla al migrar a
 * CI, cambiar por un recurso de classpath en vez de lectura de archivo.
 */
class BundleGoldenVectorTest {

    private fun vectorBytes(name: String): ByteArray {
        val file = File("../protocol/test-vectors/bundles/$name.bin")
        assertTrue(file.exists(), "No se encontró el vector dorado: ${file.absolutePath}")
        return file.readBytes()
    }

    @Test
    fun `status_trapped sobrevive round-trip byte a byte`() {
        val original = vectorBytes("status_trapped")
        val roundtripped = original.toDomainBundle().toWire()
        assertContentEquals(original, roundtripped)
    }

    @Test
    fun `observation_peer sobrevive round-trip byte a byte`() {
        val original = vectorBytes("observation_peer")
        val roundtripped = original.toDomainBundle().toWire()
        assertContentEquals(original, roundtripped)
    }

    @Test
    fun `raw_chunk sobrevive round-trip byte a byte`() {
        val original = vectorBytes("raw_chunk")
        val roundtripped = original.toDomainBundle().toWire()
        assertContentEquals(original, roundtripped)
    }
}
