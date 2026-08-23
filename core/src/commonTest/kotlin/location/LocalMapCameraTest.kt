package co.helius.core.location

import kotlin.test.Test
import kotlin.test.assertEquals

class LocalMapCameraTest {
    @Test
    fun `zoom stays within the safe interaction range`() {
        val camera = LocalMapCamera()

        assertEquals(LocalMapCamera.MIN_ZOOM, camera.zoomBy(0.1f).zoom)
        assertEquals(LocalMapCamera.MAX_ZOOM, camera.zoomBy(99f).zoom)
    }

    @Test
    fun `pan accumulates without changing zoom`() {
        val camera = LocalMapCamera().zoomBy(2f).panBy(12f, -7f).panBy(-2f, 4f)

        assertEquals(2f, camera.zoom)
        assertEquals(10f, camera.panX)
        assertEquals(-3f, camera.panY)
    }

    @Test
    fun `recenter returns to the local orientation`() {
        assertEquals(LocalMapCamera(), LocalMapCamera().zoomBy(2.5f).panBy(30f, 11f).recenter())
    }
}
