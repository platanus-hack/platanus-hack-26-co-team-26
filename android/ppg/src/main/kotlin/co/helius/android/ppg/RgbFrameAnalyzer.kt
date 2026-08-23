package co.helius.android.ppg

import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import co.helius.core.signal.ppg.FrameSample
import co.helius.core.signal.ppg.PpgConfig
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** Extracts aggregate RGB from YUV_420_888 without allocating a Bitmap. */
class RgbFrameAnalyzer(
    private val config: PpgConfig,
    private val motionProvider: () -> Float,
    private val onSample: (FrameSample) -> Unit,
) : ImageAnalysis.Analyzer {
    override fun analyze(image: ImageProxy) {
        try {
            if (image.planes.size < 3) return
            val yPlane = image.planes[0]
            val uPlane = image.planes[1]
            val vPlane = image.planes[2]
            val width = image.width
            val height = image.height
            val side = (min(width, height) * config.roiFraction).toInt().coerceAtLeast(16)
            val x0 = (width - side) / 2
            val y0 = (height - side) / 2
            val step = config.pixelStep.coerceAtLeast(1)

            val yBuf = yPlane.buffer
            val uBuf = uPlane.buffer
            val vBuf = vPlane.buffer
            var sumR = 0.0
            var sumG = 0.0
            var sumB = 0.0
            var sumY = 0.0
            var sumY2 = 0.0
            var saturated = 0
            var count = 0

            var py = y0
            while (py < y0 + side) {
                var px = x0
                while (px < x0 + side) {
                    val yi = py * yPlane.rowStride + px * yPlane.pixelStride
                    val uvX = px / 2
                    val uvY = py / 2
                    val ui = uvY * uPlane.rowStride + uvX * uPlane.pixelStride
                    val vi = uvY * vPlane.rowStride + uvX * vPlane.pixelStride
                    if (yi < yBuf.limit() && ui < uBuf.limit() && vi < vBuf.limit()) {
                        val y = yBuf.get(yi).toInt() and 0xff
                        val u = (uBuf.get(ui).toInt() and 0xff) - 128
                        val v = (vBuf.get(vi).toInt() and 0xff) - 128
                        val r = clamp(y + 1.402 * v)
                        val g = clamp(y - 0.344136 * u - 0.714136 * v)
                        val b = clamp(y + 1.772 * u)
                        sumR += r; sumG += g; sumB += b
                        sumY += y; sumY2 += y.toDouble() * y
                        if (r >= 250 || g >= 250 || b >= 250 || r <= 3) saturated++
                        count++
                    }
                    px += step
                }
                py += step
            }
            if (count == 0) return
            val meanY = sumY / count
            val variance = max(0.0, sumY2 / count - meanY * meanY)
            onSample(
                FrameSample(
                    image.imageInfo.timestamp,
                    (sumR / count).toFloat(),
                    (sumG / count).toFloat(),
                    (sumB / count).toFloat(),
                    sqrt(variance).toFloat(),
                    saturated.toFloat() / count,
                    motionProvider(),
                )
            )
        } finally {
            image.close()
        }
    }

    private fun clamp(value: Double): Double = min(255.0, max(0.0, value))
}
