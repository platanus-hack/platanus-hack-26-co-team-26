package co.helius.android.transport

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * Qué hace falta, de verdad, para que BLE funcione en este teléfono.
 *
 * Existe porque declarar los permisos en el `AndroidManifest.xml` no concede nada:
 * desde Android 12 (API 31) `BLUETOOTH_SCAN`, `BLUETOOTH_ADVERTISE` y
 * `BLUETOOTH_CONNECT` son permisos de *runtime*. La app tiene que pedirlos, y
 * `:android:app` no los pedía (solo pedía ubicación y cámara), así que el
 * transporte no podía arrancar ni con el Bluetooth encendido.
 *
 * Además de los permisos hay tres condiciones que ningún permiso cubre y que en
 * campo son la causa más común de "escanea y no encuentra nada, sin error":
 *
 *  1. **El interruptor de Ubicación del sistema.** `BLUETOOTH_SCAN` se declara sin
 *     `usesPermissionFlags="neverForLocation"`, así que Android lo trata como un
 *     permiso capaz de derivar ubicación: exige permiso de ubicación concedido *y*
 *     el servicio de ubicación encendido. Si está apagado, el escaneo devuelve cero
 *     resultados y **no** llama a `onScanFailed`.
 *  2. **El rol periférico.** Escanear (central) y anunciarse (periférico) son
 *     capacidades distintas. `FEATURE_BLUETOOTH_LE` solo garantiza la primera.
 *     Varias tablets no anuncian, y un equipo que no anuncia es invisible para los
 *     demás aunque él sí los vea — produce un descubrimiento asimétrico que parece
 *     un bug de la app.
 *  3. **El adaptador encendido.** Desde Android 13 la app no puede encender el
 *     Bluetooth por su cuenta (`BluetoothAdapter.enable()` quedó sin efecto para
 *     apps de terceros); hay que mandar al usuario a `ACTION_REQUEST_ENABLE`.
 *
 * Dueño: Helmut.
 */
object BlePermissions {

    /**
     * Permisos de runtime que la UI debe pedir, ya resueltos por nivel de API.
     * En API < 31 los permisos `BLUETOOTH*` nuevos no existen y lo que se exige es
     * ubicación fina, que es lo que habilitaba el escaneo en esas versiones.
     */
    fun required(): List<String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            listOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_ADVERTISE,
                Manifest.permission.BLUETOOTH_CONNECT,
                // Necesario mientras BLUETOOTH_SCAN no lleve neverForLocation.
                Manifest.permission.ACCESS_FINE_LOCATION,
            )
        } else {
            listOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            )
        }

    fun missing(context: Context): List<String> = required().filter {
        ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
    }

    fun hasAll(context: Context): Boolean = missing(context).isEmpty()

    private fun adapter(context: Context): BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter

    /**
     * Diagnóstico completo, pensado para mostrarse en pantalla. Cada campo en
     * `false` es una causa concreta y accionable de "no encuentra dispositivos",
     * en vez de un error genérico.
     */
    fun diagnose(context: Context): BleReadiness {
        val pm = context.packageManager
        val adapter = adapter(context)
        return BleReadiness(
            hasBleHardware = pm.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE),
            adapterEnabled = adapter?.isEnabled == true,
            canAdvertise = adapter?.isMultipleAdvertisementSupported == true &&
                adapter.bluetoothLeAdvertiser != null,
            canScan = adapter?.bluetoothLeScanner != null,
            locationServiceEnabled = isLocationServiceEnabled(context),
            missingPermissions = missing(context),
        )
    }

    private fun isLocationServiceEnabled(context: Context): Boolean {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as? android.location.LocationManager
            ?: return false
        return androidx.core.location.LocationManagerCompat.isLocationEnabled(lm)
    }
}

/**
 * Estado de preparación de BLE. `ready` exige las cinco condiciones porque en un
 * encuentro DTN los dos roles hacen falta: un teléfono que solo escanea no puede
 * ser descubierto, y uno que solo anuncia no descubre a nadie.
 */
data class BleReadiness(
    val hasBleHardware: Boolean,
    val adapterEnabled: Boolean,
    val canAdvertise: Boolean,
    val canScan: Boolean,
    val locationServiceEnabled: Boolean,
    val missingPermissions: List<String>,
) {
    val ready: Boolean
        get() = hasBleHardware && adapterEnabled && canScan &&
            locationServiceEnabled && missingPermissions.isEmpty()

    /** Motivo accionable del primer bloqueo, en el orden en que conviene resolverlos. */
    fun firstBlocker(): String? = when {
        !hasBleHardware -> "Este equipo no tiene Bluetooth LE."
        missingPermissions.isNotEmpty() ->
            "Faltan permisos: ${missingPermissions.joinToString { it.substringAfterLast('.') }}"
        !adapterEnabled -> "El Bluetooth está apagado. La app no puede encenderlo sola desde Android 13."
        !locationServiceEnabled ->
            "El servicio de Ubicación del sistema está apagado; sin él el escaneo BLE " +
                "devuelve cero resultados y no reporta error."
        !canScan -> "El adaptador no expone un escáner BLE."
        !canAdvertise ->
            "Este equipo no puede anunciarse por BLE (rol periférico no soportado): " +
                "verá a otros pero será invisible para ellos."
        else -> null
    }
}
