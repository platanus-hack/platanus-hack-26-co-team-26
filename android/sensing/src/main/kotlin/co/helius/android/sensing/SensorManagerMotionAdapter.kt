package co.helius.android.sensing

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import co.helius.core.application.ports.MotionPort
import co.helius.core.signal.motion.MotionFeatureExtractor
import co.helius.core.signal.motion.MotionSample
import co.helius.core.signal.motion.MotionWindow
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.math.sqrt

/**
 * Implementación de referencia de [MotionPort]
 * (core/application/ports/DataPorts.kt). Usa `TYPE_LINEAR_ACCELERATION`
 * (gravedad ya compensada por el sensor fusion de la plataforma -- más
 * confiable que restar 9.81 a mano, como hace el `MotionSampler` local de
 * `android/ppg`, que gatea otra cosa) + `TYPE_GYROSCOPE`. Mantiene una
 * ventana deslizante de [windowMs] y emite un [MotionWindow] resumido cada
 * [emitIntervalMs] -- el DSP (RMS/ZCR/espectro) vive en `core/signal/motion`,
 * este adaptador sólo captura y recorta.
 *
 * No pide ningún permiso runtime (ver `AndroidManifest.xml` de este módulo).
 * Si el equipo no trae alguno de los dos sensores, ese buffer queda vacío y
 * [MotionFeatureExtractor] lo trata como "sin muestras" -- degrada por
 * capacidad, nunca inventa una lectura.
 */
class SensorManagerMotionAdapter(
    private val context: Context,
    private val windowMs: Long = 10_000,
    private val emitIntervalMs: Long = 2_000,
) : MotionPort {

    private val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager

    override fun observeMotionWindows(): Flow<MotionWindow> = callbackFlow {
        val accelSensor = manager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
        val gyroSensor = manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

        val accelBuffer = ArrayDeque<MotionSample>()
        val gyroBuffer = ArrayDeque<MotionSample>()

        fun trim(buffer: ArrayDeque<MotionSample>, nowMs: Long) {
            while (buffer.isNotEmpty() && nowMs - buffer.first().timestampMs > windowMs) {
                buffer.removeFirst()
            }
        }

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                val nowMs = System.currentTimeMillis()
                val magnitude = magnitudeOf(event)
                when (event.sensor.type) {
                    Sensor.TYPE_LINEAR_ACCELERATION -> {
                        accelBuffer.addLast(MotionSample(nowMs, magnitude))
                        trim(accelBuffer, nowMs)
                    }
                    Sensor.TYPE_GYROSCOPE -> {
                        gyroBuffer.addLast(MotionSample(nowMs, magnitude))
                        trim(gyroBuffer, nowMs)
                    }
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
        }

        if (accelSensor != null) {
            manager.registerListener(listener, accelSensor, SensorManager.SENSOR_DELAY_GAME)
        }
        if (gyroSensor != null) {
            manager.registerListener(listener, gyroSensor, SensorManager.SENSOR_DELAY_GAME)
        }

        val ticker = launch {
            while (isActive) {
                delay(emitIntervalMs)
                val nowMs = System.currentTimeMillis()
                trim(accelBuffer, nowMs)
                trim(gyroBuffer, nowMs)
                if (accelBuffer.isEmpty()) continue

                val sampleRateHz = estimateSampleRateHz(accelBuffer)
                val window = MotionWindow(
                    startedAtMs = accelBuffer.first().timestampMs,
                    endedAtMs = accelBuffer.last().timestampMs,
                    sampleRateHz = sampleRateHz,
                    accel = MotionFeatureExtractor.extract(accelBuffer.toList(), sampleRateHz),
                    gyro = MotionFeatureExtractor.extract(gyroBuffer.toList(), sampleRateHz),
                    accelSamples = accelBuffer.toList(),
                )
                trySend(window)
            }
        }

        awaitClose {
            manager.unregisterListener(listener)
            ticker.cancel()
        }
    }

    private fun magnitudeOf(event: SensorEvent): Double {
        val x = event.values[0].toDouble()
        val y = event.values[1].toDouble()
        val z = event.values[2].toDouble()
        return sqrt(x * x + y * y + z * z)
    }

    private fun estimateSampleRateHz(buffer: ArrayDeque<MotionSample>): Double {
        if (buffer.size < 2) return 0.0
        val spanS = (buffer.last().timestampMs - buffer.first().timestampMs) / 1000.0
        return if (spanS > 0) (buffer.size - 1) / spanS else 0.0
    }
}
