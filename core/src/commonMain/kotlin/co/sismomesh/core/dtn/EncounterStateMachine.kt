package co.sismomesh.core.dtn

/**
 * Secuencia de encuentro (Sección 7.2), objetivo TTFC < 4 s en modo T0:
 * advertise+scan → MAGIC/SESSION → handshake (X25519+HKDF, Noise XX) → negociación de
 * capacidades → intercambio de inventarios (Bloom) → transferencia priorizada T0→T1→T2
 * → ACK/delivery receipts → registro de PeerObservation → desconexión limpia + backoff.
 * Dueño: Helmut. Testeado en JVM con LoopbackFake (sin hardware).
 */
class EncounterStateMachine {
    sealed interface State {
        object Idle : State
        object Discovering : State
        object Handshaking : State
        object NegotiatingCapabilities : State
        object ExchangingInventory : State
        object Transferring : State
        object Closing : State
    }

    fun onEvent(event: Any): State {
        TODO("dueño=Helmut")
    }
}
