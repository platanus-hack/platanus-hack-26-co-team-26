#!/usr/bin/env bash
set -euo pipefail

# Sube la tanda de documentacion tecnica y fundamentacion en fuentes reales:
# estados del arte de voz y localizacion 3D, fundamentacion juridica del habeas
# data (con dos correcciones de cita), documento de stack e integraciones,
# AltitudeFusion.kt con sus tests, el logo definitivo de HELIUS, y el arreglo
# del bit de ejecucion de gradlew.
#
# Seis commits separados para que cada uno se pueda revertir solo. Rama develop.
# Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

echo "== Rama actual (debe ser develop) =="
git branch --show-current
test "$(git branch --show-current)" = "develop" || { echo "ABORTA: no estas en develop"; exit 1; }

echo "== Estado antes de empezar =="
git status --porcelain=v1

# --------------------------------------------------------------------------- #
# 1/6 - gradlew ejecutable                                                    #
# --------------------------------------------------------------------------- #
echo
echo "== 1/6: bit de ejecucion de gradlew =="
chmod +x gradlew
git update-index --chmod=+x gradlew
git add gradlew
git commit -m "$(cat <<'EOF'
fix(build): marcar gradlew como ejecutable

gradlew estaba commiteado con modo 100644, sin bit de ejecucion, mientras
todos los demas scripts del repo (scripts/*.sh, protocol/codegen/*.sh) estan
en 100755. Los cuatro workflows que invocan ./gradlew -- android-ci,
arch-guard, protocol-ci y release -- fallan en su primer paso con
"Permission denied", antes de compilar nada.

Verificado con `git ls-files -s gradlew` y reproducido localmente.

No resuelve por si solo la construccion: el proyecto declara
sourceCompatibility 21 y los workflows instalan Temurin 17, y el wrapper fija
Gradle 8.9 que no soporta JDK 26. Ver la seccion 10 de
docs/architecture/STACK-E-INTEGRACIONES.md para el analisis completo y la
salida propuesta (jvmToolchain(21) + subir el wrapper + alinear setup-java).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 2/6 - logo                                                                  #
# --------------------------------------------------------------------------- #
echo
echo "== 2/6: logo de HELIUS =="
git add project-logo.png
git commit -m "$(cat <<'EOF'
chore: reemplazar el logo placeholder por el logo de HELIUS

Sustituye el placeholder amarillo "P/H(25)" del template del organizador por
el logo real: dos manos sosteniendo la H con la onda sismica al centro.

1000x1000 para mantener la convencion anterior (el original venia en
1254x1254). Cuantizado a 256 colores: 74 KB en vez de 285 KB, con RMSE de
0.32% y PSNR de 49.9 dB respecto al PNG sin cuantizar, o sea indistinguible a
ojo y sin bandeo visible en el degradado. Muy por debajo del limite de 500 KB
que pide platanus-hack-project.jsonc y del maxkb=2000 del hook
check-added-large-files.

El fondo queda opaco (#F7F7F7), igual que el logo anterior. Si se quiere que
se adapte al tema oscuro de GitHub habria que hacerlo transparente, y eso
altera el arte entregado, asi que se deja como decision aparte.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 3/6 - AltitudeFusion                                                        #
# --------------------------------------------------------------------------- #
echo
echo "== 3/6: AltitudeFusion + tests =="
git add core/src/commonMain/kotlin/co/helius/core/domain/location/ \
        core/src/commonTest/kotlin/location/AltitudeFusionTest.kt
git commit -m "$(cat <<'EOF'
feat(core): fusion barometrica y UWB para el eje vertical (ADR-0009)

Implementa la parte de localizacion 3D que corresponde a :core segun
ADR-0009: medicion y fusion dispositivo-a-dispositivo. El factor graph
completo que combina esto con RSSI de multiples nodos sigue siendo trabajo de
Miguel en services/localization, sin empezar.

AltitudeFusion.kt (core/domain/location/):
- Formula barometrica internacional para pasar presion a altitud relativa,
  calibrada por un parametro de escenario, nunca por una constante fija.
- Refinamiento por UWB (angulo + distancia -> componente vertical).
- Fusion ponderada por varianza inversa cuando hay ambas fuentes; nunca
  inventa la fuente que falta.
- Solo reporta un numero de piso cuando la incertidumbre alcanza (menos de
  medio piso de margen); si no, devuelve null en vez de arriesgar un piso
  equivocado, como exige el ADR.

Usa presion contra una referencia de calibracion, no presion absoluta
convertida a altitud MSL. Eso coincide con el hallazgo L2 del estado del arte
que entra en el commit siguiente: el metodo diferencial de "par de presion" es
el que alcanza ~100% de precision de piso, no la conversion absoluta.

Los tests no se pudieron ejecutar: el wrapper de Gradle no construye en este
entorno (Gradle 8.9 no soporta JDK 26) ni en CI (Temurin 17 contra
sourceCompatibility 21). Ver seccion 10 de
docs/architecture/STACK-E-INTEGRACIONES.md. Quedan commiteados para que
corran en cuanto el toolchain este arreglado.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 4/6 - estados del arte: voz y localizacion 3D                               #
# --------------------------------------------------------------------------- #
echo
echo "== 4/6: estados del arte de voz y localizacion 3D =="
git add docs/voice/PSYCHOLOGICAL-FIRST-AID-EVIDENCE.md \
        docs/architecture/LOCALIZATION-3D-STATE-OF-THE-ART.md \
        docs/architecture/ADR/0009-3d-localization.md \
        docs/voice/VOICE-GUIDANCE.md
git commit -m "$(cat <<'EOF'
docs: fundamentar la guia de voz y la localizacion 3D en literatura verificada

Las secciones de Estado del Arte del README (comunicaciones, PPG/EMG) tenian
referencias reales; la guia de voz y ADR-0009 no citaban ninguna. Estos dos
documentos cierran ese hueco con la misma exigencia: cada URL se abrio y se
confirmo que dice lo que se le atribuye antes de citarla.

docs/voice/PSYCHOLOGICAL-FIRST-AID-EVIDENCE.md
- Primeros Auxilios Psicologicos como marco (IFRC, Hobfoll et al. 2007) y
  respiracion pautada con base fisiologica replicada (Lehrer & Gevirtz 2014).
- Dice explicitamente lo que NO encontro respaldado: no hay evidencia de que
  una voz sintetica pregrabada produzca el efecto de la presencia humana en
  que se apoya el marco PFA, y la unica evidencia directa sobre IA aplicando
  PFA documenta 18.4% de alucinacion en ChatGPT-4 y 50% en Gemini.
- Revisa los 6 guiones actuales contra eso: TRAPPED_CALM y MOBILITY_CHECK ya
  siguen el patron correcto, no hay que cambiar el audio.

docs/architecture/LOCALIZATION-3D-STATE-OF-THE-ART.md
- Respalda la estructura de ADR-0009: presion diferencial como prior de piso,
  nunca como fuente unica sin calibracion, UWB como refinamiento.
- Cuantifica la degradacion que el ADR mencionaba sin numeros: UWB pasa de
  0.31-0.37 m en espacio abierto a 2.83 m con obstruccion metalica.
- Advierte que ningun estudio citado mide error en una estructura realmente
  colapsada, y agrega dos riesgos que el ADR no menciona (deriva por clima, y
  que NLOS es el caso esperado y no el raro).

Cross-links desde ADR-0009 y VOICE-GUIDANCE.md.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 5/6 - fundamentacion juridica del habeas data                               #
# --------------------------------------------------------------------------- #
echo
echo "== 5/6: fundamentacion juridica del habeas data =="
git add docs/privacy/HABEAS-DATA-FUNDAMENTACION-JURIDICA.md \
        docs/privacy/HABEAS-DATA.md \
        docs/architecture/ADR/0010-found-persons-habeas-data.md
git commit -m "$(cat <<'EOF'
docs(privacy): fundamentacion juridica del habeas data y correccion de citas

HABEAS-DATA.md mapea articulo a codigo y test, pero no respondia la pregunta
anterior a esa: bajo que titulo juridico se tratan los datos de alguien que no
autorizo nada porque estaba atrapado o inconsciente. El documento nuevo lo
contesta con las fuentes en la mano.

Aportes principales:
- El eje es el art. 6 lit. b de la Ley 1581 (interes vital + incapacidad), con
  sus dos condiciones acumulativas. Lectura comparada con el art. 9(2)(c) del
  RGPD y su Considerando 46, que menciona expresamente desastres naturales.
- El desarrollo doctrinal detallado esta en el Handbook on Data Protection in
  Humanitarian Action del CICR, 3a edicion (Marelli ed., Cambridge 2024,
  acceso abierto), seccion 3.3: enumera como casos de interes vital
  "dealing with cases of Sought Persons" y "assisting an individual who is
  unconscious or otherwise at risk, but unable to communicate Consent", que
  son literalmente los dos casos de found_persons.
- De ahi sale un cambio de prioridad real: la notificacion posterior al
  Titular no es una mejora, es una de las condiciones bajo las que se admite
  apoyarse en el interes vital. Pasa a ser el pendiente de mayor riesgo
  juridico de la lista.
- Fundamenta el rol de Responsable en la Ley 1523 de 2012 (arts. 13, 14, 27,
  45, 46), que hasta ahora era un campo `Controller` sin respaldo normativo.
- Explica por que el condicionamiento de C-748/2011 es lo que habilita la ruta
  NNA: el texto literal del art. 7 la prohibiria de plano.
- Delimita frente al Registro Nacional de Desaparecidos (Ley 589 de 2000 art.
  9, Decreto 4218 de 2005, SIRDEC, Ley 1408 de 2010): found_persons no es ese
  registro y no debe presentarse como tal.

Dos correcciones de cita en HABEAS-DATA.md:
- El limite a la supresion no esta en el Decreto 1074 art. 2.2.2.25.2.5 (ese
  compila el art. 8 del Decreto 1377, prueba de la autorizacion) sino en
  2.2.2.25.2.6 (art. 9 del Decreto 1377).
- Su redaccion no es "obstruye una actuacion judicial o administrativa" sino
  "cuando el Titular tenga un deber legal o contractual de permanecer en la
  base de datos". Retention.legal_hold debe nombrar ese deber, no un motivo
  en texto libre.
- El pendiente de notificacion citaba el art. 12, que obliga a informar al
  momento de solicitar la autorizacion y por definicion no aplica donde no se
  pidio ninguna. Reanclado en el principio de transparencia (art. 4 lit. e) y
  el art. 8 lit. c.

Cuatro pendientes nuevos derivados del analisis: acceso a Salud del ambito
responder, constancia de interes superior del NNA en el audit_log, acotar
Controller a las autoridades de la Ley 1523, y el de notificacion reordenado.

Deja escrito lo que las fuentes no resuelven: no hay jurisprudencia colombiana
que aplique el art. 6 lit. b a un desastre, ni doctrina publicada de la SIC
sobre el punto. Y lo que no se pudo verificar: el texto del art. 9 de la Ley
589 (funcionpublica.gov.co y secretariasenado.gov.co siguen fallando por TLS,
confirmado indirectamente via Ley 1408), y guia del ICO y la AEPD que devolvio
403 y 500 y por eso no se cita.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

# --------------------------------------------------------------------------- #
# 6/6 - stack e integraciones + indice del README                             #
# --------------------------------------------------------------------------- #
echo
echo "== 6/6: stack e integraciones =="
git add docs/architecture/STACK-E-INTEGRACIONES.md \
        docs/architecture/OVERVIEW.md \
        README.md \
        scripts/commit-documentacion-tecnica.sh
git commit -m "$(cat <<'EOF'
docs(architecture): stack tecnologico e integraciones reales

OVERVIEW.md dice que capas hay y por que; los ADR registran las decisiones.
Faltaba lo de en medio: que tecnologia concreta esta instalada, en que
version, quien la consume y que integraciones externas existen de verdad.
Todo derivado de leer los manifiestos del repo, no de memoria.

El documento separa cada tecnologia en tres estados -- cableado (declarado en
un build Y consumido por codigo), declarado (esta en el catalogo o en un ADR
pero ningun modulo lo usa) y pendiente -- porque sin esa distincion la tabla
de tecnologias se lee como inventario de lo que funciona.

Con ese criterio, cinco de las nueve tecnologias de la tabla de OVERVIEW.md
resultan no instaladas: deck.gl (ADR-0005; web/package.json solo trae
maplibre-gl), SQLDelight + SQLCipher (en el catalogo; :android:storage solo
depende de :core), LiteRT (comentada a proposito en android/ppg), Koin (solo
un TODO en HELIUSApp.kt, con la decision Koin-vs-Hilt abierta) y
OpenTelemetry/Loki/Tempo (cero codigo; el compose trae Jaeger y Grafana sin
colector). Se agrega nota de remision en OVERVIEW.md para que su tabla se lea
como decision y no como estado.

Documenta las integraciones con su endpoint real: EMSC por websocket
(standing order), USGS por GeoJSON con polling de 15 s, ElevenLabs con modelo
eleven_multilingual_v2 y la voz Daniela -- subrayando que no es dependencia
de ejecucion, la app nunca llama esa API -- y el SGC, incompleto por decision
razonada y no por abandono. Mas los 9 contratos de import-linter, los 6
workflows, los 8 contenedores del compose, y la nota de que found_persons usa
SQLite y no Postgres, que es la razon tecnica del pendiente de inmutabilidad
del audit_log.

Cinco inconsistencias detectadas al comparar los manifiestos, todas con
efecto verificable:

1. Ningun entorno construye el proyecto hoy. gradlew sin bit de ejecucion
   (arreglado en el primer commit de esta tanda), Temurin 17 en CI contra
   sourceCompatibility 21, y wrapper en Gradle 8.9 que no soporta JDK 26.
   Consecuencia: ningun test de Kotlin se esta ejecutando, ni en CI ni en
   local, incluidos los vectores dorados del protocolo del lado Kotlin.
2. services/shared no se instala: gtsam fija numpy<2 y el kernel pide
   numpy>=2.1, asi que el servicio api del compose no puede levantar.
3. La deteccion de deriva del protocolo cubre menos de lo que parece: una de
   las cuatro rutas del git diff (web/src/domain/protocol) no existe porque
   gen_ts.sh solo imprime un TODO, asi que ese tramo pasa siempre.
4. tools/voice_pack/README.md dice "3 guiones"; catalog.py tiene seis.
5. La guarda de vocabulario clinico falla hoy y bloquea cualquier PR. Se
   reprodujo ejecutando el comando exacto de arch-guard.yml y el del hook
   no-clinical-vocab: ambos devuelven exit 1. La lista de excepciones espera
   "nunca" o "prohibid", pero el codigo niega con "no es un diagnostico". Las
   seis lineas que dispara son usos correctos; el defecto esta en la guarda.

Corrige de paso la linea del README que declaraba 16 KB de logo (ahora 74 KB)
y agrega al indice el documento nuevo y la fundamentacion juridica.

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
test -z "$(git status --porcelain=v1)" || { echo "ABORTA: quedo algo sin commitear, revisa antes de subir"; exit 1; }

echo
echo "== Los 6 commits nuevos =="
git log --oneline origin/develop..develop

echo
echo "== Subiendo a origin/develop =="
git push origin develop

echo
echo "== Listo =="
git log --oneline -7
