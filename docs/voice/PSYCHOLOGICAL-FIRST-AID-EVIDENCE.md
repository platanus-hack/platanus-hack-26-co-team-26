# Estado del Arte — Fundamento en Primeros Auxilios Psicológicos

**Dueño:** Helmut. **Revisor de vocabulario:** Laura (ver `docs/glossary.md`).

`docs/voice/VOICE-GUIDANCE.md` documenta el diseño de ingeniería del sistema
de voz (por qué es offline, los 6 casos, cómo se genera el paquete) pero no
cita ninguna fuente sobre si calmar a una persona atrapada por voz, pedirle
respirar despacio, o pedirle un movimiento pequeño, tiene respaldo real. Esta
sección lo hace, y es tan importante lo que confirma como lo que **no**
encuentra respaldado — sección análoga a las de Comunicaciones y PPG del
`README.md` raíz, misma exigencia de fuente verificable.

**Qué está bien establecido.** Los Primeros Auxilios Psicológicos (PFA) son
un marco reconocido internacionalmente (OMS, Federación Internacional de la
Cruz Roja y de la Media Luna Roja) para ayudar a alguien en una crisis aguda,
estructurado en tres acciones — **Mirar, Escuchar, Vincular** — y apoyado en
los cinco principios de Hobfoll et al. (2007) para intervención en trauma
masivo: seguridad, calma, autoeficacia/eficacia colectiva, conexión y
esperanza [V1][V2]. La respiración lenta y pautada (~6 respiraciones por
minuto, exhalación más larga que la inhalación) tiene una base fisiológica
sólida y replicada: activa el barorreflejo y la vía vagal aferente, aumenta
medible y consistentemente la variabilidad de frecuencia cardíaca (HRV), y es
el mecanismo detrás del biofeedback de HRV usado clínicamente desde hace más
de una década [V4]. Ninguna de las dos cosas es específica de emergencias
sísmicas — son fundamentos generales de apoyo en crisis y de fisiología
respiratoria — pero ambas están bien establecidas en su propio dominio.

**Qué está en debate o es frontera activa.** Que una **voz sintética
pregrabada**, sin la persona real detrás, logre el mismo efecto que un
humano aplicando PFA es una pregunta abierta, no una premisa demostrada. El
propio marco PFA se apoya en presencia, escucha activa y respuesta a lo que
la persona expresa — cosas que un guion fijo, sin importar cuán bien escrito,
no puede hacer [V1]. La única evidencia directa encontrada sobre IA aplicando
PFA es un estudio de 2025 que compara ChatGPT-4 y Gemini en escenarios de
desastre por *texto*: ChatGPT-4 alcanzó buen desempeño en los principios
básicos (72%) pero el propio estudio señala que "la efectividad del PFA
suele depender de la conexión humana, incluyendo el tono, el lenguaje
corporal y las expresiones faciales; estos elementos están ausentes" en una
interacción con IA, y documenta una tasa real de alucinación (información
falsa generada) del 18.4% en ChatGPT-4 y 50% en Gemini — una preocupación de
seguridad seria en un contexto de crisis [V3]. No se encontró ningún estudio
sobre voz sintética específicamente (ni sobre esta situación específica:
alguien atrapado en escombros). La honestidad aquí importa: HELIUS no está
aplicando una técnica clínicamente validada para este escenario exacto, está
**tomando prestados principios de un marco validado para un problema
adyacente** (apoyo humano en crisis) y aplicándolos a un guion de voz fijo,
sin retroalimentación de la persona — una diferencia real, no cosmética.

**Dónde está la frontera.** Pedir un movimiento pequeño y deliberado durante
una espera prolongada bajo estrés agudo —en vez de dejar a la persona
completamente pasiva— tiene una lógica de sentido común (mantener alguna
sensación de control/agencia) pero **no se encontró literatura específica
sobre confinamiento físico tras un colapso estructural** que la respalde
directamente; la literatura de activación conductual disponible es sobre
depresión y estrés general, no sobre esta situación [búsqueda documentada,
sin cita citable]. Lo que sí es real y no debe ignorarse es la guía operativa
de rescate: las evaluaciones de riesgo de bomberos para colapsos
estructurales documentan que las estructuras colapsadas pueden contener
huecos ("voids") donde una persona atrapada puede sobrevivir períodos largos,
y que remover o alterar escombros sin entender la distribución de carga
puede causar un colapso secundario [V5]. Esa guía está dirigida a quien
rescata, no a quien está atrapado, pero la implicación es directa: **pedirle
a alguien atrapado que se mueva nunca debe ignorar el riesgo de que ese
movimiento perturbe su propio entorno inmediato** — es exactamente el tipo
de cautela que `MOBILITY_CHECK` y `GYRO_SOS_PATTERN` ya intentan capturar
("no te fuerces", "sin poner en riesgo"), pero conviene que quede explícito
que esa cautela tiene una razón de ingeniería estructural detrás, no solo de
bienestar emocional.

> [!CAUTION]
> Este sistema de voz está **informado por** principios de Primeros Auxilios
> Psicológicos y por fisiología respiratoria básica — no es una intervención
> clínica validada, no reemplaza a un profesional de salud mental, y no hay
> evidencia específica de que una voz sintética pregrabada produzca el mismo
> efecto que la presencia humana en la que se basa el marco PFA. Nunca
> presentar los guiones como "terapia" o "primeros auxilios psicológicos
> certificados" — son guía informada, con esa limitación explícita.

## Qué implica esto para los guiones actuales

Revisando el texto real de los 6 guiones en `docs/voice/VOICE-GUIDANCE.md`
contra lo anterior:

1. **`TRAPPED_CALM` ya sigue el patrón correcto de respiración** — "inhala
   contando hasta cuatro, sostén, exhala contando hasta seis" tiene exhalación
   más larga que inhalación, consistente con [V4]. No hace falta cambiarlo.
2. **`MOBILITY_CHECK` ya evita forzar el movimiento** ("No hagas ningún
   esfuerzo grande... si moverte te causa dolor o te pone en riesgo, no te
   fuerces") — alineado con la cautela de [V5], aunque el guion no explicita
   *por qué* (riesgo de perturbar el entorno, no solo de lastimarse). No es
   necesario alargar el guion para explicarlo — pero si el equipo agrega más
   guiones a futuro, esta razón (estructural, no solo médica) debería quedar
   en la justificación de diseño, no necesariamente en el audio.
3. **Ningún guion actual afirma ser "terapia" o intervención clínica** — ya
   cumple `docs/glossary.md`. Lo que sí falta, y esta sección lo cubre ahora,
   es la honestidad explícita (aquí, no en el audio que escucha la persona)
   de que la evidencia detrás de "voz sintética calma a alguien atrapado" es
   una extrapolación razonable de PFA humano, no un hecho probado para este
   escenario exacto.

## Referencias

| ID | Fuente | URL |
|---|---|---|
| V1 | IFRC Reference Centre for Psychosocial Support. *A Guide to Psychological First Aid, for Red Cross and Red Crescent Societies.* Copenhagen, 2018. ISBN 978-87-92490-53-7. | https://pscentre.org/wp-content/uploads/2019/05/PFA-Guide-low-res.pdf |
| V2 | Hobfoll, S.E., Watson, P., Bell, C.C., et al. (2007). *Five essential elements of immediate and mid-term mass trauma intervention: Empirical evidence.* Psychiatry, 70(4), 283–315. (Citado en V1, p.14.) | — |
| V3 | Tan, J.T., Gan, R.K., Alsua, C., et al. (2025). *Psychological First Aid by AI: Proof-of-Concept and Comparative Performance of ChatGPT-4 and Gemini in Different Disaster Scenarios.* Journal of Clinical Psychology, 81(8), 726–738. | https://doi.org/10.1002/jclp.23808 |
| V4 | Lehrer, P.M. & Gevirtz, R. (2014). *Heart rate variability biofeedback: how and why does it work?* Frontiers in Psychology, 5, 756. | https://doi.org/10.3389/fpsyg.2014.00756 |
| V5 | Department for Communities and Local Government / Chief Fire and Rescue Adviser (UK). *Fire and Rescue Authorities Operational Guidance — Generic Risk Assessment 2.1: Rescues from confined spaces, 2.1.4 collapsed structures.* TSO, abril 2013. ISBN 9780117540934. | https://insarag.org/wp-content/uploads/2016/04/2_1_4_Rescues_from_Confined_spaces_-_Collapsed_Structures.pdf |

*Verificado el 23 de agosto de 2026 — cada URL de esta tabla fue obtenida por
búsqueda y su contenido confirmado por lectura directa, no citado de
memoria. Donde no se encontró una fuente real y verificable para una
afirmación plausible (voz sintética específicamente, activación conductual
en confinamiento estructural específicamente), esta sección lo dice
explícitamente en vez de inventar una cita.*
