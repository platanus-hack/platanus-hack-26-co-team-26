package co.helius

import android.app.Application

/**
 * Dueño: Laura + Jorge (app Android, diseño y desarrollo). DI con Koin (ligero, sin
 * generación de código) o Hilt si el equipo lo prefiere — decisión pendiente, ver
 * docs/team/DIVISION-DE-TRABAJO.md.
 */
class HELIUSApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // TODO(dueño=Laura/Jorge): iniciar Koin/Hilt, ver android/app/src/main/kotlin/co/helius/di/
    }
}
