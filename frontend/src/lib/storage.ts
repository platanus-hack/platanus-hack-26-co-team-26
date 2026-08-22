// sessionStorage envuelto en try/catch (privado/bloqueado no debe romper la app) — ver
// specs de la corrida del 2026-08-22: cada pantalla (Analisis/Loop) persiste su ULTIMA
// corrida por separado, para que cambiar de pestana y volver no la pierda. Un F5 tambien la
// conserva (dura toda la sesion del tab, no sobrevive a cerrar el navegador).

export function readSession<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function writeSession<T>(key: string, value: T): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    // no disponible -> el estado sigue andando solo en memoria
  }
}
