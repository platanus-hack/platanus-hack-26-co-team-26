package co.sismomesh.android.transport

import co.sismomesh.core.crypto.BeaconAuthenticator
import co.sismomesh.core.domain.vo.BeaconPayload
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Codifica/decodifica el beacon BLE de 23 bytes (protocol/beacon/BEACON_FORMAT.md,
 * presupuesto ≤26 B). `sessionKey` es la clave del incidente (compartida por
 * invitación/QR antes del desastre, Sección 9.6) — no es una clave por peer;
 * autentica "esto viene de alguien con la clave del incidente", no identifica
 * a la persona (eso es el `ephemeralNodeId`, ya pseudónimo).
 */
object BleBeaconCodec {
    private const val MAGIC_0: Byte = 0x5A
    private const val MAGIC_1: Byte = 0x4D
    const val WIRE_SIZE = 23

    fun encode(version: Int, beacon: BeaconPayload, sessionKey: ByteArray): ByteArray {
        require(beacon.ephemeralNodeId.size == 8) { "ephemeralNodeId debe ser 8 bytes" }
        val withoutAuth = ByteBuffer.allocate(WIRE_SIZE - 4).order(ByteOrder.LITTLE_ENDIAN)
        withoutAuth.put(MAGIC_0)
        withoutAuth.put(MAGIC_1)
        withoutAuth.put(version.toByte())
        withoutAuth.putShort(beacon.sessionHash)
        withoutAuth.put(beacon.ephemeralNodeId)
        withoutAuth.put(beacon.flags)
        withoutAuth.put(beacon.battery)
        withoutAuth.put(beacon.status)
        withoutAuth.putShort(beacon.seq)
        withoutAuth.put(beacon.hops)
        val head = withoutAuth.array()
        val auth = BeaconAuthenticator.computeAuth(head, sessionKey)
        return head + auth
    }

    /** Devuelve null si el MAGIC no coincide (no es un beacon SismoMesh) o el AUTH no verifica. */
    fun decode(wire: ByteArray, sessionKey: ByteArray): Decoded? {
        if (wire.size != WIRE_SIZE) return null
        if (wire[0] != MAGIC_0 || wire[1] != MAGIC_1) return null

        val head = wire.copyOfRange(0, WIRE_SIZE - 4)
        val auth = wire.copyOfRange(WIRE_SIZE - 4, WIRE_SIZE)
        val expectedAuth = BeaconAuthenticator.computeAuth(head, sessionKey)
        if (!auth.contentEquals(expectedAuth)) return null

        val buf = ByteBuffer.wrap(wire).order(ByteOrder.LITTLE_ENDIAN)
        buf.position(2) // saltar MAGIC
        val version = buf.get().toInt() and 0xff
        val sessionHash = buf.short
        val ephemeralNodeId = ByteArray(8).also { buf.get(it) }
        val flags = buf.get()
        val battery = buf.get()
        val status = buf.get()
        val seq = buf.short
        val hops = buf.get()

        return Decoded(
            version = version,
            beacon = BeaconPayload(sessionHash, ephemeralNodeId, flags, battery, status, seq, hops),
        )
    }

    data class Decoded(val version: Int, val beacon: BeaconPayload)
}
