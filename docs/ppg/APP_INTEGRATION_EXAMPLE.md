# Ejemplo de conexión con la aplicación

## ViewModel

```kotlin
class PhysioAssessmentViewModel(
    private val engine: PpgEngine,
) : ViewModel() {
    val engineState = engine.state
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PpgSessionState.Idle)

    val progress = engine.progress
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PpgProgress())

    fun start() = viewModelScope.launch {
        runCatching { engine.start() }
            .onFailure { /* el engine ya publica Failed/Cancelled */ }
    }

    fun cancel() = viewModelScope.launch { engine.cancel() }

    override fun onCleared() {
        viewModelScope.launch { engine.cancel() }
    }
}
```

## Mapeo UI

```kotlin
fun PpgSessionState.toUiState(): PhysioUiState = when (this) {
    PpgSessionState.Idle -> PhysioUiState.Ready
    PpgSessionState.Preparing -> PhysioUiState.Loading("Preparando cámara")
    PpgSessionState.Stabilizing -> PhysioUiState.Guide("Mantén el dedo quieto")
    PpgSessionState.Acquiring -> PhysioUiState.Capturing
    PpgSessionState.Processing -> PhysioUiState.Loading("Analizando señal")
    is PpgSessionState.Completed -> PhysioUiState.Result(result)
    is PpgSessionState.QualityRejected -> PhysioUiState.Retry(quality.reasons)
    is PpgSessionState.Failed -> PhysioUiState.Error(message)
    PpgSessionState.Cancelled -> PhysioUiState.Ready
}
```

## Uso en una pantalla

```kotlin
when (val state = uiState) {
    PhysioUiState.Ready -> StartButton(onClick = viewModel::start)
    is PhysioUiState.Guide -> FingerPlacementGuide(state.message)
    PhysioUiState.Capturing -> CaptureProgress(progress.fraction)
    is PhysioUiState.Retry -> QualityRetry(state.reasons, viewModel::start)
    is PhysioUiState.Result -> ResultCard(
        observation = state.value.ifo,
        pulseBpm = state.value.features?.pulseBpm,
        estimatedEcg = state.value.estimatedEcg.takeIf {
            it.status == EstimatedEcgStatus.AVAILABLE
        },
    )
    else -> Unit
}
```

El ejemplo es deliberadamente independiente de Compose/XML; la app puede mapear los mismos estados a su framework actual.
