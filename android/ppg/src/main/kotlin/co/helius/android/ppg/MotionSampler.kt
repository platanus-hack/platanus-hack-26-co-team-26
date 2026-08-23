package co.helius.android.ppg

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.sqrt

/** Maintains a cheap high-pass proxy of device motion from the accelerometer. */
class MotionSampler(context: Context) : SensorEventListener {
    private val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer = manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    @Volatile private var magnitude = 0f
    private var gravity = 9.81f

    fun start() {
        accelerometer?.let { manager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
    }

    fun stop() = manager.unregisterListener(this)
    fun current(): Float = magnitude

    override fun onSensorChanged(event: SensorEvent) {
        val x = event.values[0]; val y = event.values[1]; val z = event.values[2]
        val total = sqrt(x * x + y * y + z * z)
        gravity = 0.96f * gravity + 0.04f * total
        magnitude = 0.8f * magnitude + 0.2f * kotlin.math.abs(total - gravity)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
