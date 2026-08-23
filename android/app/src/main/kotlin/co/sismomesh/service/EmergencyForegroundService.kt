package co.sismomesh.service

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * El detalle que decide el proyecto (Sección 7.3): corre el motor DTN de verdad,
 * no cuando el sistema lo permite. START_STICKY, sin dependencia de timers exactos
 * ("hacer trabajo cuando el sistema despierta", no "despertar a las 14:03:00").
 *
 * Ciclo de trabajo por modo (Sección 7.4):
 *   READY    → WorkManager periódico + geofencing + BLE scan oportunista
 *   ALERT    → arranque inmediato de este servicio
 *   TRAPPED  → notificación persistente, wakelock parcial acotado
 *   RESCUER  → pantalla activa + GNSS alta precisión
 *
 * Probado contra la matriz de fabricantes (Sección 17.4) — cada uno mata procesos
 * de forma distinta (Xiaomi, Huawei, Oppo, Samsung, Motorola, Tecno/Infinix).
 *
 * Dueño: Laura + Jorge (app) — revisor obligatorio: Helmut (consumo de batería del
 * motor DTN que este servicio hospeda).
 */
class EmergencyForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        TODO("dueño=Laura/Jorge: promoteToForeground() + arrancar EncounterStateMachine de :core")
    }
}
