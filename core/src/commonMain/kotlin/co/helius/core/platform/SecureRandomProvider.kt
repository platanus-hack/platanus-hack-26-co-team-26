package co.helius.core.platform

/**
 * Patrón expect/actual (Sección 4.2): se usa SOLO cuando la diferencia es de plataforma
 * (aleatoriedad segura, reloj monótono, almacén de claves) — no para lógica de dominio,
 * que siempre vive como interfaz normal + inyección (puertos en application/ports).
 *
 * `actual` en androidMain usa SecureRandom respaldado por el proveedor del sistema.
 * `actual` en iosMain queda TODO(fase 2) — ver docs/roadmap/VERTICAL-SLICES.md § 19bis.
 */
expect fun secureRandomBytes(n: Int): ByteArray
