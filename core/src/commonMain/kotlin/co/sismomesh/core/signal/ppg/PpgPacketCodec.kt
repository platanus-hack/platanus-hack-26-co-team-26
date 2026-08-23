package co.sismomesh.core.signal.ppg

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.roundToInt

// TODO(fase 2, dueño=Helmut): java.nio no es portable a iosMain. Mientras el
// target iOS esté desactivado (ver core/src/iosMain/README.md) esto es seguro;
// antes de activarlo, mover a expect/actual o a una librería multiplataforma de
// buffers (p. ej. kotlinx-io).

/** Formato binario compacto de 28 bytes — especificación completa en protocol/ppg/PPG_PACKET_V1.md. */
object PpgPacketCodec {
    fun encode(
        sessionId: Long,
        unixSeconds: Long,
        quality: SignalQuality,
        features: SignalFeatures?,
        classification: Classification,
    ): ByteArray {
        val out = ByteBuffer.allocate(28).order(ByteOrder.LITTLE_ENDIAN)
        out.put(0x50.toByte()); out.put(0x47.toByte()); out.put(1.toByte())
        var flags = 0
        if (quality.accepted) flags = flags or 1
        if (classification.approvedAiUsed) flags = flags or 2
        flags = flags or 4
        if (QualityReason.MOTION in quality.reasons) flags = flags or 8
        out.put(flags.toByte())
        out.putLong(sessionId)
        out.putInt(unixSeconds.toInt())
        out.put(u8(features?.pulseBpm, 255))
        out.put(quality.score.coerceIn(0, 100).toByte())
        out.put(classification.observation.code.toByte())
        out.put(u8(classification.confidence?.times(100f), 255))
        out.putShort(u16(features?.medianIbiMs, 65535))
        out.putShort(u16(features?.shortRmssdMs, 65535))
        out.put(reasonMask(quality.reasons).toByte())
        out.put(0x10.toByte()) // preprocessor major=1, model major=0
        val bytes = out.array()
        val crc = crc16(bytes, 0, 26)
        out.putShort(crc.toShort())
        return bytes
    }

    private fun u8(value: Float?, unknown: Int) = (value?.roundToInt()?.coerceIn(0, 254) ?: unknown).toByte()
    private fun u16(value: Float?, unknown: Int) = (value?.roundToInt()?.coerceIn(0, 65534) ?: unknown).toShort()
    private fun reasonMask(reasons: Set<QualityReason>): Int = reasons.fold(0) { acc, r -> acc or (1 shl (r.ordinal.coerceAtMost(7))) }

    private fun crc16(data: ByteArray, start: Int, length: Int): Int {
        var crc = 0xffff
        for (i in start until start + length) {
            crc = crc xor ((data[i].toInt() and 0xff) shl 8)
            repeat(8) { crc = if (crc and 0x8000 != 0) (crc shl 1) xor 0x1021 else crc shl 1; crc = crc and 0xffff }
        }
        return crc
    }
}
