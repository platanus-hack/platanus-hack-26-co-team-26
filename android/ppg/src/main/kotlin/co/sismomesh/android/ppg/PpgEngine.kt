package co.sismomesh.android.ppg

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.camera2.CaptureRequest
import android.os.Build
import android.os.PowerManager
import android.util.Size
import androidx.camera.camera2.interop.Camera2CameraControl
import androidx.camera.camera2.interop.CaptureRequestOptions
import androidx.camera.camera2.interop.ExperimentalCamera2Interop
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import co.sismomesh.core.signal.ppg.Classification
import co.sismomesh.core.signal.ppg.ComponentVersions
import co.sismomesh.core.signal.ppg.EstimatedEcg
import co.sismomesh.core.signal.ppg.EstimatedEcgReconstructor
import co.sismomesh.core.signal.ppg.EstimatedEcgStatus
import co.sismomesh.core.signal.ppg.FrameSample
import co.sismomesh.core.signal.ppg.IfoFusionEngine
import co.sismomesh.core.signal.ppg.PhysiologicalClassifier
import co.sismomesh.core.signal.ppg.PhysiologicalObservation
import co.sismomesh.core.signal.ppg.PpgConfig
import co.sismomesh.core.signal.ppg.PpgErrorCode
import co.sismomesh.core.signal.ppg.PpgEngineException
import co.sismomesh.core.signal.ppg.PpgPacketCodec
import co.sismomesh.core.signal.ppg.PpgProgress
import co.sismomesh.core.signal.ppg.PpgResult
import co.sismomesh.core.signal.ppg.PpgSessionState
import co.sismomesh.core.signal.ppg.PpgSignalProcessor
import co.sismomesh.core.signal.ppg.SafetyFirstClassifier
import co.sismomesh.core.signal.ppg.SignalQualityEvaluator
import co.sismomesh.core.signal.ppg.UnavailableEstimatedEcgReconstructor
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.guava.await
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import java.security.SecureRandom
import java.util.Collections
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Implementación de referencia de `PpgCaptureIPort` (core/application/ports/SensingPorts.kt).
 * TODO(dueño=Laura/Jorge): cablear detrás de esa interfaz cuando se integre con
 * `PpgSessionController`/DI de android/app; por ahora expone su propio contrato
 * `PpgEngine`, consumible directamente.
 */
interface PpgEngine {
    val state: StateFlow<PpgSessionState>
    val progress: StateFlow<PpgProgress>
    suspend fun start(config: PpgConfig = PpgConfig()): PpgResult
    suspend fun cancel()
}

@OptIn(ExperimentalCamera2Interop::class)
class CameraXPpgEngine(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner,
    private val classifier: PhysiologicalClassifier = SafetyFirstClassifier(),
    private val ecgReconstructor: EstimatedEcgReconstructor = UnavailableEstimatedEcgReconstructor(),
    private val ifoFusion: IfoFusionEngine = IfoFusionEngine(),
) : PpgEngine {
    private val mutex = Mutex()
    private val _state = MutableStateFlow<PpgSessionState>(PpgSessionState.Idle)
    private val _progress = MutableStateFlow(PpgProgress())
    override val state = _state.asStateFlow()
    override val progress = _progress.asStateFlow()
    private var activeCompletion: CompletableDeferred<Unit>? = null
    private var provider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var executor: ExecutorService? = null
    private var motion: MotionSampler? = null

    override suspend fun start(config: PpgConfig): PpgResult = mutex.withLock {
        val samples = Collections.synchronizedList(mutableListOf<FrameSample>())
        val completion = CompletableDeferred<Unit>()
        activeCompletion = completion
        _progress.value = PpgProgress()
        _state.value = PpgSessionState.Preparing
        var firstTimestampNs: Long? = null
        val requiredNs = config.acquisitionSeconds * 1_000_000_000L
        val stabilizationNs = config.stabilizationMs * 1_000_000L
        val exposureLocked = AtomicBoolean(false)
        var lockExposure: () -> Unit = {}

        try {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                throw PpgEngineException(PpgErrorCode.CAMERA_PERMISSION_DENIED, "Permiso de cámara no concedido")
            }
            if (Build.VERSION.SDK_INT >= 29) {
                val power = context.getSystemService(Context.POWER_SERVICE) as PowerManager
                if (power.currentThermalStatus >= PowerManager.THERMAL_STATUS_SEVERE) {
                    throw PpgEngineException(PpgErrorCode.THERMAL_LIMIT, "Temperatura del dispositivo demasiado alta")
                }
            }
            val localProvider = try {
                ProcessCameraProvider.getInstance(context).await()
            } catch (t: Throwable) {
                throw PpgEngineException(PpgErrorCode.CAMERA_BIND_FAILED, "No fue posible iniciar CameraX", t)
            }
            provider = localProvider
            if (!localProvider.hasCamera(CameraSelector.DEFAULT_BACK_CAMERA)) {
                throw PpgEngineException(PpgErrorCode.BACK_CAMERA_UNAVAILABLE, "Cámara trasera no disponible")
            }
            val localMotion = MotionSampler(context).also { it.start() }
            motion = localMotion
            val localExecutor = Executors.newSingleThreadExecutor().also { executor = it }
            val analyzer = RgbFrameAnalyzer(config, localMotion::current) { sample ->
                val first = firstTimestampNs ?: sample.timestampNs.also { firstTimestampNs = it }
                val elapsed = sample.timestampNs - first
                if (elapsed < stabilizationNs) {
                    _state.value = PpgSessionState.Stabilizing
                    return@RgbFrameAnalyzer
                }
                if (exposureLocked.compareAndSet(false, true)) lockExposure()
                _state.value = PpgSessionState.Acquiring
                samples += sample
                val acquired = elapsed - stabilizationNs
                _progress.value = PpgProgress((acquired.toDouble() / requiredNs).toFloat().coerceIn(0f, 1f))
                if (acquired >= requiredNs) completion.complete(Unit)
            }
            val analysis = ImageAnalysis.Builder()
                .setTargetResolution(Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()
                .also { it.setAnalyzer(localExecutor, analyzer) }

            val localCamera = try {
                withContext(Dispatchers.Main) {
                    localProvider.unbindAll()
                    localProvider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, analysis)
                }
            } catch (t: Throwable) {
                throw PpgEngineException(PpgErrorCode.CAMERA_BIND_FAILED, "No fue posible vincular la cámara", t)
            }
            camera = localCamera
            if (!localCamera.cameraInfo.hasFlashUnit()) {
                throw PpgEngineException(PpgErrorCode.TORCH_UNAVAILABLE, "El dispositivo no dispone de flash trasero")
            }
            try {
                localCamera.cameraControl.enableTorch(true).await()
            } catch (t: Throwable) {
                throw PpgEngineException(PpgErrorCode.TORCH_UNAVAILABLE, "No fue posible encender el flash", t)
            }
            lockExposure = {
                runCatching {
                    val options = CaptureRequestOptions.Builder()
                        .setCaptureRequestOption(CaptureRequest.CONTROL_AE_LOCK, true)
                        .build()
                    Camera2CameraControl.from(localCamera.cameraControl).setCaptureRequestOptions(options)
                }
            }

            withTimeout(config.sessionTimeoutSeconds * 1000L) { completion.await() }
            cleanup()
            _state.value = PpgSessionState.Processing
            val snapshot = synchronized(samples) { samples.toList() }
            val processed = PpgSignalProcessor().process(snapshot, config.targetSampleRateHz)
            val quality = SignalQualityEvaluator().evaluate(snapshot, processed, config)
            val classification = if (processed != null) classifier.classify(processed, quality)
            else Classification(PhysiologicalObservation.UNRELIABLE_MEASUREMENT, null, false)
            val estimatedEcg = when {
                !quality.accepted -> EstimatedEcg(EstimatedEcgStatus.QUALITY_REJECTED)
                processed == null -> EstimatedEcg(EstimatedEcgStatus.UNAVAILABLE)
                else -> ecgReconstructor.reconstruct(processed)
            }
            val ifo = ifoFusion.evaluate(quality, classification, estimatedEcg)
            val sessionId = SecureRandom().nextLong()
            val features = processed?.features?.takeIf { quality.accepted }
            val packet = PpgPacketCodec.encode(
                sessionId, System.currentTimeMillis() / 1000L, quality, features, classification
            )
            val result = PpgResult(
                sessionId, quality, features, classification, estimatedEcg, ifo, packet, ComponentVersions()
            )
            _state.value = if (quality.accepted) PpgSessionState.Completed(result)
            else PpgSessionState.QualityRejected(quality)
            result
        } catch (t: TimeoutCancellationException) {
            cleanup()
            _state.value = PpgSessionState.Failed("La captura excedió el tiempo permitido", PpgErrorCode.SESSION_TIMEOUT)
            throw PpgEngineException(PpgErrorCode.SESSION_TIMEOUT, "Tiempo de captura agotado", t)
        } catch (t: Throwable) {
            cleanup()
            if (t is kotlinx.coroutines.CancellationException) {
                _state.value = PpgSessionState.Cancelled
            } else {
                val code = (t as? PpgEngineException)?.errorCode ?: PpgErrorCode.INTERNAL_PROCESSING_ERROR
                _state.value = PpgSessionState.Failed(t.message ?: "Error de adquisición PPG", code)
            }
            throw t
        } finally {
            activeCompletion = null
        }
    }

    override suspend fun cancel() {
        activeCompletion?.cancel()
        cleanup()
        _state.value = PpgSessionState.Cancelled
    }

    private suspend fun cleanup() {
        try { camera?.cameraControl?.enableTorch(false)?.await() } catch (_: Throwable) { }
        withContext(Dispatchers.Main) { runCatching { provider?.unbindAll() } }
        motion?.stop(); motion = null
        executor?.shutdownNow(); executor = null
        camera = null; provider = null
    }
}
