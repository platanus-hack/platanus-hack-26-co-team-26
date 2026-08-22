# SismoMesh · app Flutter (Android)

Scaffold escrito a mano. **Falta la carcasa nativa**, que la genera Flutter.

## Arranque (una sola vez, ~10 min)

```bash
# 1. Genera android/, ios/, .metadata, etc. SIN pisar lib/ ni pubspec.yaml.
cd apps/mobile
flutter create --org us.platanus.sismomesh --platforms=android --project-name sismomesh .

# 2. flutter create SOBRESCRIBE el AndroidManifest. Restaurar el nuestro:
git checkout android/app/src/main/AndroidManifest.xml

# 3. minSdk 26 en android/app/build.gradle (o build.gradle.kts):
#      minSdkVersion 26
#      targetSdkVersion 34

flutter pub get
flutter run -d <device-id>          # flutter devices para listarlos
```

> `flutter create` sobre un directorio existente respeta `lib/` y `pubspec.yaml`,
> pero **sí** reescribe `AndroidManifest.xml`. El paso 2 no es opcional: sin
> nuestros permisos, Nearby no descubre a nadie y falla en silencio.

## Mapa de propiedad

| Carpeta | Dueño | Qué contiene |
|---|---|---|
| `lib/protocol/` | D3 | Bundle v1, JSON canónico, Ed25519, hash. **Congelado**: cambios avisan a todos |
| `lib/store/` | D1 | `BundleStore` en sqflite + motor DTN store-carry-forward |
| `lib/transport/` | D2 | `TransportAdapter`, Nearby Connections, preflight de permisos |
| `lib/gateway/` | D1/D3 | Subida por lotes con `Idempotency-Key` |
| `lib/app/` | D1 | `MeshController`, roles, feature flags |
| `lib/ui/` | D4 | Pantallas |
| `lib/core/` | D1 | Log en anillo |

## Invariantes que no se tocan

1. **`payloadBytes` es la fuente de verdad.** Nunca re-serializar el payload al
   reenviar ni al verificar. Es lo que hace que la firma sobreviva N saltos y
   cruce el límite Dart↔Python sin romperse.
2. **`relay` va fuera de la firma.** Cada salto añade su capa; nadie reescribe
   la evidencia original.
3. **No existe `DEAD`** en `NodeStatus`, y no se agrega.
4. **`null` = no medido.** Nunca cero, nunca un valor por defecto. La UI lo
   pinta como *sin dato*, no como un medidor en cero.
5. **Lo no soportado se oculta, no se simula.** `capabilities()` decide.

## Apuntar al backend

`MeshController(gatewayUrl: ...)` en `lib/main.dart`:

- emulador Android → `http://10.0.2.2:8000`
- teléfono físico → `http://<IP-del-laptop>:8000` (misma Wi-Fi/hotspot)

## Estado

Implementado: protocolo firmado, store persistente, DTN con inventario y
dedupe, transporte Nearby, subida idempotente, UI de 4 pantallas.

Sin implementar (campos ya presentes en `null`): PPG, movimiento, localización
por zona, voz offline. Ver `docs/CORE-5H.md` §9.
