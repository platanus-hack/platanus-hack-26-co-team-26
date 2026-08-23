package co.helius.android.transport

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Framing mínimo para partir un bundle serializado en escrituras/notificaciones
 * GATT del tamaño del MTU negociado. El MTU por defecto de BLE es 23 B (20 B
 * útiles); tras `gatt.requestMtu()` puede llegar a 517 B, pero **no todos los
 * fabricantes lo conceden** (ver docs/validation/VALIDATION.md, matriz de
 * dispositivos) — por eso el chunking es obligatorio, nunca asumir MTU grande.
 *
 * Formato de cada chunk: [messageId:2B][chunkIndex:2B][totalChunks:2B][payload...]
 */
object BleChunking {
    const val HEADER_SIZE = 6

    fun chunk(messageId: Int, payload: ByteArray, maxChunkPayload: Int): List<ByteArray> {
        require(maxChunkPayload > 0) { "maxChunkPayload debe ser positivo" }
        val totalChunks = ((payload.size + maxChunkPayload - 1) / maxChunkPayload).coerceAtLeast(1)
        return (0 until totalChunks).map { index ->
            val start = index * maxChunkPayload
            val end = minOf(start + maxChunkPayload, payload.size)
            val body = payload.copyOfRange(start, end)
            ByteBuffer.allocate(HEADER_SIZE + body.size).order(ByteOrder.LITTLE_ENDIAN)
                .putShort(messageId.toShort())
                .putShort(index.toShort())
                .putShort(totalChunks.toShort())
                .put(body)
                .array()
        }
    }

    fun parseHeader(chunk: ByteArray): Header {
        require(chunk.size >= HEADER_SIZE) { "Chunk demasiado corto para contener el header" }
        val buf = ByteBuffer.wrap(chunk).order(ByteOrder.LITTLE_ENDIAN)
        val messageId = buf.short.toInt() and 0xffff
        val index = buf.short.toInt() and 0xffff
        val total = buf.short.toInt() and 0xffff
        return Header(messageId, index, total)
    }

    fun payloadOf(chunk: ByteArray): ByteArray = chunk.copyOfRange(HEADER_SIZE, chunk.size)

    data class Header(val messageId: Int, val chunkIndex: Int, val totalChunks: Int)
}

/**
 * Reensambla chunks que pueden llegar fuera de orden (best-effort sobre BLE).
 * Un mensaje se considera completo cuando se recibieron todos sus índices.
 * No thread-safe por diseño -- se usa desde el callback GATT, que ya serializa
 * las invocaciones en un único hilo del sistema.
 */
class BleReassembler {
    private val inProgress = mutableMapOf<Int, MutableMap<Int, ByteArray>>()
    private val totalsByMessage = mutableMapOf<Int, Int>()

    /** Devuelve el mensaje completo y reensamblado, o null si aún faltan chunks. */
    fun accept(chunk: ByteArray): ByteArray? {
        val header = BleChunking.parseHeader(chunk)
        val body = BleChunking.payloadOf(chunk)

        val parts = inProgress.getOrPut(header.messageId) { mutableMapOf() }
        parts[header.chunkIndex] = body
        totalsByMessage[header.messageId] = header.totalChunks

        if (parts.size < header.totalChunks) return null

        val ordered = (0 until header.totalChunks).map { i -> parts[i] ?: return null }
        inProgress.remove(header.messageId)
        totalsByMessage.remove(header.messageId)
        return ordered.reduce { acc, b -> acc + b }
    }
}
