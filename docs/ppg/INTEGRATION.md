# Contrato de integración para la app Android

## API pública propuesta

```kotlin
interface PpgEngine {
    val state: StateFlow<PpgSessionState>
    val progress: StateFlow<PpgProgress>
    suspend fun start(config: PpgConfig = PpgConfig()): PpgResult
    suspend fun cancel()
}
```

La pantalla no debe controlar cámara o torch directamente. Solo observa estado y progreso.

## Estados que debe manejar la UI

| Estado | Comportamiento UI |
|---|---|
| `Preparing` | Solicitar cámara y preparar sensor |
| `Stabilizing` | “Cubre cámara y flash sin presionar” |
| `Acquiring` | Progreso y feedback de contacto/movimiento |
| `Processing` | Bloquear doble inicio; puede durar milisegundos |
| `Completed` | Mostrar observaciones y calidad |
| `QualityRejected` | Explicar motivo concreto y permitir repetir |
| `Failed` | Mensaje recuperable, sin resultado fisiológico |

## Mensajes de guía

- `NO_FINGER`: “Cubre completamente la cámara y el flash con la yema.”
- `TOO_MUCH_PRESSURE`: “Reduce un poco la presión del dedo.”
- `MOVEMENT`: “Mantén el teléfono y el dedo quietos.”
- `SATURATED`: “Ajustando iluminación; mantén el dedo en posición.”
- `COLD_OR_LOW_SIGNAL`: “La señal es débil. Prueba otro dedo no lesionado.”

## Permisos

Solo `android.permission.CAMERA`. No solicitar micrófono ni almacenamiento para PPG.

## Ciclo de vida

- Vincular CameraX al `LifecycleOwner` de la pantalla.
- `onStop`: cancelar y apagar torch.
- Cambio de configuración: conservar estado en ViewModel o cancelar limpiamente.
- Una sola sesión simultánea mediante `Mutex`.
- No ejecutar si la batería/temperatura obliga a una restricción severa; retornar error recuperable.

## Resultado

```kotlin
data class PpgResult(
    val sessionId: Long,
    val quality: SignalQuality,
    val features: SignalFeatures?,
    val classification: Classification,
    val estimatedEcg: EstimatedEcg,
    val ifo: IfoResult,
    val packet: ByteArray,
    val versions: ComponentVersions
)
```

`features` es nulo si la medición no pasó calidad. Nunca sustituir valores desconocidos por cero.

## FastAPI

FastAPI no forma parte del camino urgente. Endpoints opcionales:

```text
GET  /v1/ppg/models/manifest
GET  /v1/ppg/models/{version}
POST /v1/ppg/research-sessions   # solo consentimiento de investigación
POST /v1/ppg/validation-results  # datos anonimizados/consentidos
```

No enviar cuadros ni PPG al backend por defecto. La descarga de modelos debe comprobar firma/hash y conservar rollback local.

## Definición de terminado para la integración

- La app funciona en modo avión.
- No aparece ningún MP4/JPEG en almacenamiento o caché.
- Torch se apaga en éxito, cancelación, excepción y background.
- La medición mala nunca produce clase fisiológica.
- Rotación o doble toque no crean dos sesiones.
- Pasa pruebas en al menos un dispositivo Camera2 LEGACY, LIMITED y FULL.
- El payload se decodifica bit a bit con golden vectors.
