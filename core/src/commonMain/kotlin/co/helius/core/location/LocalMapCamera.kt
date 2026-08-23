package co.helius.core.location

/**
 * Estado pequeño y puro de la cámara de orientación local.
 *
 * No representa una cámara cartográfica con teselas: conserva únicamente el
 * zoom y el desplazamiento de la superficie de orientación que el shell puede
 * renderizar sin inventar calles, personas o coordenadas remotas.
 */
data class LocalMapCamera(
    val zoom: Float = 1f,
    val panX: Float = 0f,
    val panY: Float = 0f,
) {
    fun panBy(deltaX: Float, deltaY: Float): LocalMapCamera = copy(
        panX = panX + deltaX,
        panY = panY + deltaY,
    )

    fun zoomBy(factor: Float): LocalMapCamera = copy(
        zoom = (zoom * factor.coerceAtLeast(0.01f)).coerceIn(MIN_ZOOM, MAX_ZOOM),
    )

    fun recenter(): LocalMapCamera = LocalMapCamera()

    companion object {
        const val MIN_ZOOM = 1f
        const val MAX_ZOOM = 4f
    }
}
