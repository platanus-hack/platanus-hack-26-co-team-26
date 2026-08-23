package co.helius.android.sensing

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import co.helius.core.application.ports.MotionSample
import co.helius.core.application.ports.MotionSensorSource
import co.sismomesh.core.location.MotionState
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlin.math.sqrt

class AndroidMotionSensorSource(context: Context) : MotionSensorSource {
    private val manager = context.applicationContext.getSystemService(SensorManager::class.java)

    override fun observeMotion(): Flow<MotionSample> = callbackFlow {
        val accelerometer = manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        val gyroscope = manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        if (accelerometer == null) { close(); return@callbackFlow }
        var angularVelocity: Double? = null
        val window = ArrayDeque<Double>(20)
        val listener = object : SensorEventListener {
            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
            override fun onSensorChanged(event: SensorEvent) {
                val magnitude = sqrt(event.values.sumOf { (it * it).toDouble() })
                if (event.sensor.type == Sensor.TYPE_GYROSCOPE) { angularVelocity = magnitude; return }
                if (window.size == 20) window.removeFirst()
                window.addLast(magnitude)
                if (window.size < 20) return
                val mean = window.average()
                val variance = window.sumOf { (it - mean) * (it - mean) } / window.size
                val rms = sqrt(window.sumOf { it * it } / window.size)
                val energy = sqrt(variance)
                val state = when { energy > 4.0 -> MotionState.RAPID_MOVEMENT; energy > 0.8 -> MotionState.MOVING; energy < 0.25 -> MotionState.STATIONARY; else -> MotionState.UNKNOWN }
                trySend(MotionSample(rms, variance, angularVelocity, event.timestamp, state))
            }
        }
        manager.registerListener(listener, accelerometer, SensorManager.SENSOR_DELAY_GAME)
        gyroscope?.let { manager.registerListener(listener, it, SensorManager.SENSOR_DELAY_GAME) }
        awaitClose { manager.unregisterListener(listener) }
    }
}
