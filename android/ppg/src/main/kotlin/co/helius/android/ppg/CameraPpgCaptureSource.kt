package co.helius.android.ppg

import android.content.Context
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import co.helius.core.application.ports.PpgCapturePort
import co.helius.core.application.ports.PpgFrame
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/** Camera + flash acquisition only. It does not infer a diagnosis or an ECG signal. */
class CameraPpgCaptureSource(
    context: Context,
    private val lifecycleOwner: LifecycleOwner,
    private val previewView: PreviewView? = null,
) : PpgCapturePort {
    private val appContext = context.applicationContext

    override fun captureSession(durationS: Int): Flow<PpgFrame> = callbackFlow {
        val providerFuture = ProcessCameraProvider.getInstance(appContext)
        var provider: ProcessCameraProvider? = null
        var camera: androidx.camera.core.Camera? = null
        val analysis = ImageAnalysis.Builder()
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
        val startedAt = System.currentTimeMillis()
        analysis.setAnalyzer(ContextCompat.getMainExecutor(appContext)) { image ->
            val frame = image.toPpgFrame()
            image.close()
            if (frame != null && System.currentTimeMillis() - startedAt <= durationS * 1_000L) trySend(frame)
            if (System.currentTimeMillis() - startedAt > durationS * 1_000L) {
                camera?.cameraControl?.enableTorch(false)
                provider?.unbind(analysis)
                close()
            }
        }
        providerFuture.addListener({
            runCatching {
                provider = providerFuture.get()
                provider?.unbindAll()
                val preview = previewView?.let { view ->
                    androidx.camera.core.Preview.Builder().build().also { it.setSurfaceProvider(view.surfaceProvider) }
                }
                camera = if (preview != null) provider?.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
                else provider?.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, analysis)
                camera?.cameraControl?.enableTorch(true)
            }.onFailure { close(it) }
        }, ContextCompat.getMainExecutor(appContext))
        awaitClose {
            camera?.cameraControl?.enableTorch(false)
            provider?.unbind(analysis)
            analysis.clearAnalyzer()
        }
    }
}

private fun ImageProxy.toPpgFrame(): PpgFrame? {
    val plane = planes.firstOrNull() ?: return null
    val buffer = plane.buffer
    if (!buffer.hasRemaining()) return null
    val rgba = ByteArray(buffer.remaining())
    buffer.get(rgba)
    var red = 0L
    var green = 0L
    var blue = 0L
    var count = 0
    var index = 0
    while (index + 3 < rgba.size) {
        red += rgba[index].toInt() and 0xFF
        green += rgba[index + 1].toInt() and 0xFF
        blue += rgba[index + 2].toInt() and 0xFF
        count++
        index += 4
    }
    if (count == 0) return null
    val contact = (green / count.toDouble() / 255.0).coerceIn(0.0, 1.0)
    return PpgFrame(System.currentTimeMillis(), red / count.toDouble(), green / count.toDouble(), blue / count.toDouble(), contact)
}
