#!/usr/bin/env bash
set -euo pipefail

# Sube la tanda de arreglos de build, niveles de API y BLE, mas el reporte de
# verificacion y pendientes. Cinco commits separados para que cada uno se pueda
# revertir solo. Rama develop.
#
# IMPORTANTE, y esta en el reporte que se commitea: el build verde
# (clean build + 62 tests + lint + APK) se verifico ANTES de integrar el commit
# 2a69b5f de Laura (1904 lineas nuevas sin compilar). El build sobre el merge NO
# se pudo ejecutar por falta de tiempo -- es el pendiente 4.1 del reporte.
#
# Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

echo "== Rama actual (debe ser develop) =="
git branch --show-current
test "$(git branch --show-current)" = "develop" || { echo "ABORTA: no estas en develop"; exit 1; }

echo "== Estado antes de empezar =="
git status --porcelain=v1

# --------------------------------------------------------------------------- #
# 1/5 - toolchain: dependencias nuevas del catalogo                           #
# --------------------------------------------------------------------------- #
echo
echo "== 1/5: catalogo de versiones y dependencias =="
git add gradle/libs.versions.toml core/build.gradle.kts \
        android/sensing/build.gradle.kts android/ppg/build.gradle.kts \
        android/transport/build.gradle.kts
git commit -m "$(cat <<'EOF'
build: androidx.annotation y core-ktx donde hacian falta para compilar

Tres modulos usaban APIs que no tenian declaradas como dependencia:

- :core necesita androidx.annotation para @RequiresApi, que marca el piso de
  API 33 de X25519/XDH en el proveedor JCA de Android sin recurrir a
  @Suppress("NewApi") -- suprimir habria tapado un crash real en Android 12.
- :android:sensing necesita androidx.core-ktx para LocationManagerCompat y
  ContextCompat, el backport de getCurrentLocation (API 30) y getMainExecutor
  (API 28) hasta el minSdk 26 del proyecto.
- :android:ppg y :android:transport necesitan androidx.annotation para
  androidx.annotation.OptIn y @RequiresPermission respectivamente.

Se conserva play-services-nearby que entro en 2ff52aa; el conflicto del bloque
de dependencias de :android:transport se resolvio sumando ambas.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 2/5 - niveles de API: crashes reales en Android 8-12                        #
# --------------------------------------------------------------------------- #
echo
echo "== 2/5: compatibilidad de nivel de API =="
git add core/src/androidMain/kotlin/co/helius/core/crypto/Identity.kt \
        android/sensing/src/main/kotlin/co/helius/android/sensing/AndroidLocationSource.kt \
        android/ppg/src/main/kotlin/co/helius/android/ppg/CameraPpgCaptureSource.kt \
        android/ppg/src/main/kotlin/co/helius/android/ppg/PpgEngine.kt
git commit -m "$(cat <<'EOF'
fix(android): tres rutas que reventaban en Android 8-12 con minSdk 26

Encontrados al poder correr lint por primera vez (el proyecto no compilaba en
ningun entorno del equipo, ver docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md).
Los tres compilaban y fallaban en ejecucion, en la gama baja que el proyecto se
compromete a soportar.

1. core/crypto/Identity.kt -- X25519/XDH solo existen en el proveedor JCA de
   Android desde API 33 (Conscrypt). Con minSdk 26, el handshake cifrado moria
   con NoClassDefFoundError sobre XECPublicKeySpec o NoSuchAlgorithmException
   desde getInstance("X25519"), errores que no dicen nada en un log de campo.
   Ahora X25519Handshake.isSupported() sondea el proveedor -- no compara
   SDK_INT, porque los tests corren en JVM de escritorio donde X25519 existe
   desde JDK 15 y SDK_INT vale 0, y un chequeo por nivel de API habria dado
   "no soportado" justo donde si funciona. El sondeo ademas cubriria solo un
   BouncyCastle registrado como proveedor extra, que es la mitigacion que el
   propio encabezado del archivo ya prescribia. Toda la superficie queda
   marcada con @RequiresApi(33).

2. android/sensing AndroidLocationSource -- usaba
   LocationManager#getCurrentLocation (API 30) y Context#mainExecutor (API 28)
   sin guarda. Sustituidos por LocationManagerCompat y ContextCompat, que
   hacen el backport sin cambiar el comportamiento en equipos nuevos.

3. android/ppg CameraPpgCaptureSource -- Context#mainExecutor (API 28) en dos
   sitios. Mismo arreglo.

Ademas :android:ppg:lintDebug fallaba con UnsafeOptInUsageError: el @OptIn de
Kotlin no lo reconoce el lint de AGP, que pide androidx.annotation.OptIn. Se
extrajo lockAutoExposure() con las dos anotaciones (una para el compilador,
otra para lint) en vez de silenciar el chequeo.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 3/5 - BLE: por que el descubrimiento no encontraba nada                     #
# --------------------------------------------------------------------------- #
echo
echo "== 3/5: transporte BLE =="
git add android/transport/src/main/kotlin/co/helius/android/transport/BlePermissions.kt \
        android/transport/src/main/kotlin/co/helius/android/transport/BleTransport.kt \
        android/transport/src/main/kotlin/co/helius/android/transport/BleGattClient.kt \
        android/transport/src/main/kotlin/co/helius/android/transport/BleGattServer.kt
git commit -m "$(cat <<'EOF'
fix(transport): el scan no podia encontrar nada, y un fallo era permanente

Diagnostico de lo que se reporto en pruebas con dos tablets y un movil ("no
sincroniza, no pasa nada, y una vez que marca error siempre marca error").
Tres bugs de codigo, no de los equipos:

1. EL FILTRO DE SCAN NO PODIA COINCIDIR CON EL ANUNCIO, NUNCA. startAdvertising
   pone el beacon en service data (AD type 0x16) y a proposito no incluye una
   lista de service UUID, por el presupuesto de 31 B del legacy advertising.
   Pero observePeers filtraba con ScanFilter.setServiceUuid(...), que compara
   contra ScanRecord.getServiceUuids(), vacio cuando solo hay service data.
   Resultado: escaneo activo, cero resultados y ningun error -- exactamente el
   "no pasa nada". Corregido a setServiceData con mascara vacia; el beacon se
   sigue validando despues por MAGIC + AUTH en BleBeaconCodec.

2. UN FALLO DE SCAN ERA TERMINAL. onScanFailed hacia close(excepcion) sobre un
   callbackFlow, y un flow cerrado no se reabre: el primer error dejaba el
   descubrimiento muerto hasta reiniciar el proceso. Eso explica el "de ahi en
   adelante marca error". Ahora hay reintento con backoff, y el caso
   SCAN_FAILED_SCANNING_TOO_FREQUENTLY espera la ventana completa: el sistema
   limita a 5 startScan por cada 30 s, asi que tocar "buscar" cinco veces
   inutilizaba el descubrimiento.

3. LOS FALLOS DEL RADIO ERAN INVISIBLES. onStartFailure del advertising era un
   TODO vacio: un telefono que no anunciaba se veia identico a uno que si.
   Ahora BleRadioEvent los expone con el codigo traducido.

Nuevo BlePermissions: cubre lo que ningun permiso arregla y que en campo es la
causa mas comun de "escanea y no encuentra nada".

- Los permisos BLUETOOTH_SCAN/ADVERTISE/CONNECT son de runtime desde Android 12
  y la app NUNCA los pedia (solo pedia ubicacion y camara).
- BLUETOOTH_SCAN se declara sin neverForLocation, asi que exige el interruptor
  de Ubicacion del sistema encendido; apagado, el scan devuelve cero resultados
  sin llamar a onScanFailed.
- Rol periferico: FEATURE_BLUETOOTH_LE solo garantiza escanear.
  isMultipleAdvertisementSupported dice si el equipo puede anunciarse. Es la
  hipotesis principal para la Redmi Pad SE: si no anuncia, ve a otros pero es
  invisible, y el descubrimiento se ve asimetrico.
- BleReadiness.firstBlocker() da el motivo accionable en vez de "error".

Los 18 MissingPermission de lint se resolvieron declarando @RequiresPermission
en la superficie real (BleTransport, BleGattClient, BleGattServer), no con
@SuppressLint: el permiso queda en la firma y lint lo verifica en el llamador.

stop() pasa a best-effort a proposito: soltar recursos no debe lanzar porque el
usuario revoco un permiso mientras la app corria.

NO VERIFICADO EN RADIO. Guia de prueba en dispositivos y el diagnostico de dos
minutos con nRF Connect en
docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md seccion 4.2.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 4/5 - test contradictorio                                                    #
# --------------------------------------------------------------------------- #
echo
echo "== 4/5: AltitudeFusionTest =="
git add core/src/commonTest/kotlin/location/AltitudeFusionTest.kt
git commit -m "$(cat <<'EOF'
fix(test): AltitudeFusionTest tenia dos casos contradictorios entre si

Con el build funcionando por primera vez, 62 tests corrieron y este fallaba.
"pressure equal to reference" esperaba piso 0 con pisos de 3 m y la
incertidumbre base de 3 m; "floor number requires enough certainty" esperaba
null para exactamente el mismo caso. La regla de ADR-0009 -- no reportar piso
si la incertidumbre supera medio piso -- dice que el segundo es el correcto, y
es lo que implementa floorOf.

Se corrige el primero: estar EN el punto de referencia no autoriza a reportar
el piso, la regla no tiene excepcion para "altitud = 0". Se agrega la
comprobacion complementaria con pisos de 6 m, donde el mismo margen si alcanza
y el piso si es 0, para que el test cubra los dos lados de la frontera.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 5/5 - reporte de verificacion y pendientes                                   #
# --------------------------------------------------------------------------- #
echo
echo "== 5/5: reporte de verificacion y pendientes =="
git add docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md \
        scripts/commit-build-y-ble.sh
git commit -m "$(cat <<'EOF'
docs: reporte de que se verifico por ejecucion y que queda pendiente

Documento honesto de estado, para que nadie asuma que algo funciona porque
esta escrito. Separa lo ejecutado de lo no ejecutado.

VERIFICADO POR EJECUCION: clean build de Kotlin con 62 tests y lint de los 8
modulos, APK debug de 14 MB, ruff limpio en los dos servicios Python, 47 + 95
tests de pytest, y lint/test/build de web.

Incluye lo que hacia falta para que el proyecto compile y que no estaba escrito
en ninguna parte: JDK 21 (17 no compila con sourceCompatibility 21, y el
wrapper Gradle 8.9 no soporta JDK 26) y el Android SDK con platform 35.

PENDIENTES, con prioridad y comandos:

1. El build verde se verifico ANTES de integrar el commit 2a69b5f de Laura, que
   trae 1904 lineas nuevas nunca compiladas (MobileShell +934,
   NearbyConnectionsTransport +318, OperationalModes +111). El build sobre el
   merge no se pudo ejecutar por falta de tiempo. Es la prioridad 1.
2. Prueba de BLE en hardware, con el diagnostico de dos minutos via nRF Connect
   y los ajustes de MIUI/HyperOS que ningun permiso cubre (autostart, bateria
   sin restricciones, ubicacion del sistema).
3. Cinco de las 13 rutas de la UI eran PlaceholderScreen antes del commit de
   Laura, incluidas MAP, EMERGENCY (el boton rojo "NECESITO AYUDA" navegaba a
   un maniqui) y NEARBY. Sobre el mapa: no existe ninguna libreria de mapas en
   Android -- MapLibre solo esta en web/package.json -- pese a que el texto del
   placeholder dice "Base MapLibre lista" y ADR-0005 la declara. Y
   EmergencyForegroundService.onStartCommand era un TODO(...), o sea que
   arrancar el servicio crasheaba. Hay que revisar cuales de estas resolvio el
   commit de Laura.
4. ktlint, detekt y konsist estan declarados con apply false y ningun modulo los
   aplica: "./gradlew ktlintCheck" responde "Task not found", asi que
   android-ci, arch-guard, make lint y make arch-check fallan por tarea
   inexistente. Se dejo sin aplicar a proposito para no mezclar un reformateo
   masivo con los arreglos funcionales; queda como trabajo post-commit con los
   comandos listos.
5. La guarda de vocabulario clinico devuelve exit 1 hoy y bloquea todo PR: su
   lista de excepciones espera "nunca" o "prohibid", pero el codigo niega con
   "no es un diagnostico". Las seis lineas que dispara son usos correctos.

Incluye tambien el inventario de las 5 ramas remotas y el plan de consolidacion
en main, con el criterio de conservar la documentacion de main y complementarla
con la de develop sin borrar lo que no deba borrarse.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# Verificacion y push                                                          #
# --------------------------------------------------------------------------- #
echo
echo "== Nada debe quedar sin commitear (salvo ignorados) =="
git status --porcelain=v1
test -z "$(git status --porcelain=v1)" || { echo "ABORTA: quedo algo sin commitear"; exit 1; }

echo
echo "== Commits nuevos =="
git log --oneline origin/develop..develop

echo
echo "== Subiendo a origin/develop =="
git fetch origin
if ! git merge-base --is-ancestor origin/develop develop; then
  echo "origin/develop avanzo mientras corria esto; rebase antes de subir"
  git rebase origin/develop
fi
git push origin develop

echo
echo "== Listo =="
git log --oneline -6
echo
echo "SIGUIENTE PASO (prioridad 1, en el PC de Laura):"
echo "  export JAVA_HOME=/ruta/a/jdk-21 && export PATH=\"\$JAVA_HOME/bin:\$PATH\""
echo "  export ANDROID_HOME=\"\$HOME/Android/Sdk\" && echo \"sdk.dir=\$ANDROID_HOME\" > local.properties"
echo "  ./gradlew clean build :android:app:assembleDebug"
echo "  # detalle completo: docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md"
