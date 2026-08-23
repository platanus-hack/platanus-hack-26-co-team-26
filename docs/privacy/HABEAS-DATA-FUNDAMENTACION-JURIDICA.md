# Fundamentación jurídica — habeas data en `found_persons`

**Ámbito:** `services/found_persons`.
**Dueño:** Miguel. **Revisores:** Helmut (cifrado break-glass), Laura (NNA y vocabulario).

[`HABEAS-DATA.md`](HABEAS-DATA.md) mapea artículo por artículo a código y test: sirve
para auditar qué se implementó. No responde una pregunta anterior a esa, y que es la
que decide si el servicio puede existir: **¿bajo qué título jurídico se tratan los datos
de una persona que no autorizó nada porque estaba atrapada o inconsciente?** Este
documento contesta eso con las fuentes en la mano, y deja anotado lo que las fuentes no
alcanzan a resolver.

El orden es deliberado. Primero qué clase de derecho está en juego, porque de eso
depende la carga probatoria. Luego cuál es la única base de legitimación disponible en
el escenario central. Después qué condiciones trae esa base, porque son las que se
traducen en requisitos de código. Y al final, tres cosas que se encontraron revisando:
dos estándares externos más estrictos que los nuestros, un error de cita en la
documentación vigente, y las preguntas que quedan abiertas.

---

## 1. El habeas data no es un deber de confidencialidad, es un derecho de control

El artículo 15 de la Constitución reconoce a toda persona el derecho a "conocer,
actualizar y rectificar" las informaciones que se hayan recogido sobre ella en bancos de
datos [H1]. La consecuencia práctica es que no basta con custodiar bien el dato: hay que
poder demostrarle al Titular qué se tiene, de dónde salió y quién lo consultó. Un
servicio que protege el dato pero no puede rendir esa cuenta incumple igual.

La Ley 1581 de 2012 es estatutaria, de modo que pasó por control previo de
constitucionalidad en la Sentencia C-748 de 2011 [H2][H3]. Esto importa por una razón
concreta y no formal: varios de sus artículos quedaron declarados exequibles **de manera
condicionada**, y el condicionamiento —no el texto literal— es la norma aplicable. El
caso de los datos de niños, niñas y adolescentes (sección 8) es el ejemplo donde esa
diferencia decide el comportamiento del código.

## 2. En el escenario central no hay autorización que recoger, y eso no es un vacío

El servicio existe para registrar que una persona apareció. En su caso de uso principal
esa persona está atrapada, inconsciente o incomunicada. Pedirle autorización es
imposible, y esperar a que pueda darla anula la utilidad del registro.

La ley prevé exactamente esa situación. El artículo 6 prohíbe tratar datos sensibles
—salud y biométricos entre ellos— salvo causal tasada, y su literal b) dice, textualmente:

> "El Tratamiento sea necesario para salvaguardar el interés vital del Titular y este se
> encuentre física o jurídicamente incapacitado." [H2]

Dos condiciones acumulativas, no una: que el tratamiento sea **necesario** para
salvaguardar el interés vital, y que el Titular esté **incapacitado** para consentir. La
segunda es la que impide que la causal se estire. Mientras la persona pueda autorizar, la
causal no está disponible aunque el interés vital sea evidente.

De ahí se sigue algo que el código ya hace pero que conviene tener fundamentado: la
causal `VITAL_INTEREST_INCAPACITY` no es una de varias alternativas cómodas, es la única
que sobrevive al escenario central, y por eso es también la que exige más disciplina.
`PUBLIC_AUTHORITY_DUTY` (art. 10 lit. a) no la sustituye: habilita datos no sensibles sin
autorización, no datos de salud ni biométricos.

## 3. La causal no es una invención local, y su lectura comparada acota su alcance

El artículo 6 lit. b) reproduce una estructura que viene del derecho europeo. El artículo
9(2)(c) del RGPD admite el tratamiento de categorías especiales cuando "processing is
necessary to protect the vital interests of the data subject or of another natural person
where the data subject is physically or legally incapable of giving consent" [H6]. Misma
lógica, mismos dos requisitos.

Lo que el derecho europeo añade, y que en Colombia no está escrito en ninguna parte, es
la constancia explícita de que un desastre natural cuenta como escenario de interés
vital. El Considerando 46 del RGPD dice, textualmente:

> "Some types of processing may serve both important grounds of public interest and the
> vital interests of the data subject as for instance when processing is necessary for
> humanitarian purposes, including for monitoring epidemics and their spread or in
> situations of humanitarian emergencies, in particular in situations of natural and
> man-made disasters." [H6]

Es la referencia más cercana a una afirmación de derecho positivo de que un sismo activa
esta base. No es vinculante en Colombia y no se cita como si lo fuera; se cita porque la
norma colombiana comparte redacción y origen, y porque no se encontró jurisprudencia ni
doctrina de la SIC que resuelva el punto en el ámbito interno (sección 11).

El mismo Considerando impone un límite que sí tiene efecto en el diseño:

> "Processing of personal data based on the vital interest of another natural person
> should in principle take place only where the processing cannot be manifestly based on
> another legal basis." [H6]

Cuando quien consulta es la familia, el interés vital invocado es **de otra persona**, y
en esa hipótesis la causal es subsidiaria: solo procede si no hay otra base disponible.
Traducido al servicio, una consulta de ámbito `family` no debería ampararse en interés
vital si el propio Titular ya autorizó o si el Responsable tiene un título propio para
informar.

## 4. La doctrina humanitaria es donde la causal está desarrollada en detalle

El desarrollo más específico que se encontró no está en derecho de datos general sino en
la doctrina de acción humanitaria. El *Handbook on Data Protection in Humanitarian
Action* del CICR, tercera edición (Marelli ed., Cambridge University Press, 2024, acceso
abierto) dedica su sección 3.3 al interés vital y define su alcance así: procede cuando
el tratamiento es necesario para proteger un interés esencial para "the Data Subject's
life, integrity, health, dignity or security or that of another person" [H7].

Entre los casos que enumera aparecen dos que describen este servicio con precisión
literal:

> "The Humanitarian Organization is dealing with cases of Sought Persons."
>
> "The Humanitarian Organization is assisting an individual who is unconscious or
> otherwise at risk, but unable to communicate Consent." [H7]

Y su glosario define *Sought Person* como "a person unaccounted for, for whom a tracing
operation has been launched" [H7]. El capítulo sobre drones lo aplica al caso de búsqueda
y rescate: su uso "would most likely qualify under this legal basis, because it would
protect the vital interest of the Data Subject (i.e. the person unaccounted for)", y
agrega que "strict standards should therefore be applied to determine whether this legal
basis is present" [H7].

Lo decisivo, sin embargo, no es el respaldo sino las **condiciones** que la doctrina
adjunta. Para apoyarse en interés vital, el Handbook exige tres cosas: tener elementos
suficientes para considerar que sin el tratamiento la persona quedaría en riesgo de daño
físico o moral; dar información clara sobre el tratamiento propuesto; y asegurar que la
persona esté en posición de ejercer su derecho de oposición "as soon and as clearly as
possible" [H7]. La sección 3.3 lo repite para este supuesto:

> "the Humanitarian Organization should, if possible, ensure that the Data Subjects are
> aware of the Processing as soon as possible, that they have sufficient knowledge to
> understand and appreciate the specified purpose(s) for which Personal Data are
> collected and processed, and are in a position to object to the Processing if they so
> wish." [H7]

En la misma línea, la Resolución 33IC/19/R4 de la 33ª Conferencia Internacional de la
Cruz Roja y de la Media Luna Roja (Ginebra, 9–12 de diciembre de 2019), sobre
restablecimiento del contacto entre familiares y privacidad, insta a garantizar que los
datos personales no sean "requested or used for purposes incompatible with the
humanitarian nature of the work of the Movement, [...] or in a manner that would
undermine the trust of the people it serves" [H8]. Es el fundamento externo de dos
decisiones que el servicio ya tomó: que `Purpose` sea un enum cerrado y contrastado por
operación, y que no exista búsqueda por texto libre.

## 5. Consecuencia concreta: la notificación posterior no es una mejora, es un requisito

Aquí es donde la fundamentación cambia el estado del proyecto en vez de solo respaldarlo.

`HABEAS-DATA.md` lista como pendiente la "notificación al Titular cuando se entró por
causal excepcional y la persona recupera la capacidad de decidir". Bajo la lectura
anterior, ese pendiente no es un ítem de cortesía: la posibilidad de conocer el
tratamiento y oponerse es una de las tres condiciones bajo las cuales la doctrina admite
apoyarse en interés vital [H7]. Mientras no exista el canal, la causal se está usando sin
una de sus condiciones constitutivas. Es el pendiente de mayor riesgo jurídico de la
lista, y debería ordenarse como tal.

Conviene además corregir el fundamento normativo con que ese pendiente está citado hoy.
El artículo 12 de la Ley 1581 impone informar al Titular "al momento de solicitar [...]
la autorización" [H2]: por definición no aplica a un caso donde no se solicitó
autorización alguna. El anclaje correcto en derecho interno es el principio de
transparencia (art. 4 lit. e) junto con el derecho del art. 8 lit. c a ser informado del
uso dado a los datos, y en doctrina, la condición del Handbook citada arriba.

## 6. Dos estándares externos son más estrictos que el nuestro

**Datos de salud.** El Handbook sostiene que los datos de salud "should be kept separate
from other Personal Data, and should only be accessible by health-care providers or
personnel specifically delegated by the" responsable [H7]. La tabla de minimización por
ámbito de `HABEAS-DATA.md` concede hoy la categoría Salud al ámbito `responder`
completo. Un rescatista no es necesariamente personal sanitario ni personal delegado, de
modo que hay una divergencia real entre el diseño y el estándar. No se propone cambiarla
por decreto —puede haber una razón operativa sólida para que el rescatista vea una nota
de cuidado— pero debe ser una decisión registrada y motivada, no una omisión.

**Datos biométricos.** El mismo texto es tajante sobre la relación entre biometría e
interés vital: "If these data are intended to be used for the entire duration of an
individual's life, then the legal basis of that person's vital interest will most likely
not be applicable, and Consent should be acquired instead" [H7]. Esto respalda
directamente la exigencia de caducidad que el dominio ya impone a toda causal
excepcional: un `biometric_ref` sin fecha de vencimiento deja de estar cubierto por la
causal que lo habilitó. El Handbook añade una advertencia que vale tener presente al
justificar el campo: con frecuencia la biometría responde a "the Humanitarian
Organizations' need to carry out their work in an efficient and effective manner [...]
rather than responding to the vital interests of the individuals concerned" [H7]. La
eficiencia del sistema no es interés vital del Titular. El techo actual, que reserva
biométricos al ámbito `authority`, es consistente con esa cautela.

## 7. Quién puede ser el Responsable no es una decisión de producto

`HABEAS-DATA.md` asigna el rol de Responsable del Tratamiento a "la autoridad del
incidente" y lo materializa en el campo `Controller`, sin decir de dónde sale esa
autoridad. La Ley 1523 de 2012, que adopta la política nacional de gestión del riesgo de
desastres y crea el Sistema Nacional de Gestión del Riesgo (SNGRD), lo responde: su
artículo 14 hace del alcalde el "responsable directo de la implementación de los procesos
de gestión del riesgo" en el municipio, el artículo 13 fija el papel equivalente del
gobernador, y el artículo 27 crea los consejos departamentales, distritales y municipales
de gestión del riesgo como instancias de coordinación [H9].

De ahí se derivan dos cosas para el código. La primera es que `Controller` no puede ser
un campo de texto libre: el conjunto de entidades que legítimamente pueden ocupar ese rol
está delimitado por la Ley 1523, y la inscripción en el RNBD (art. 25 de la Ley 1581)
corresponde a esa entidad, no a HELIUS, que actúa como Encargado. La segunda es que los
artículos 45 y 46 de la misma ley ya ordenan un sistema nacional de información para la
gestión del riesgo y sistemas territoriales interoperables con él [H9]: la
interoperabilidad no es una aspiración del roadmap sino una expectativa normativa
preexistente que conviene no ignorar al diseñar la salida de datos.

## 8. En niños, niñas y adolescentes, el condicionamiento de C-748 es lo que habilita

El texto literal del artículo 7 de la Ley 1581 es prohibitivo:

> "Queda proscrito el Tratamiento de datos personales de niños, niñas y adolescentes,
> salvo aquellos datos que sean de naturaleza pública." [H2]

Leído solo, ese artículo impediría de plano registrar el hallazgo de un menor. Lo que
hace viable la ruta NNA del servicio es el condicionamiento de la Corte: al declarar
exequible el artículo 7, la Sentencia C-748 de 2011 precisó que los datos de menores de
18 años, cualquiera sea su naturaleza, pueden ser objeto de tratamiento siempre que no
ponga en riesgo la prevalencia de sus derechos fundamentales y responda de manera
inequívoca a la realización del principio del interés superior del NNA [H3].

La consecuencia operativa es exigente y no está cubierta hoy. La habilitación no depende
de que exista un representante legal que autorice, sino de que el tratamiento **satisfaga
el interés superior**, que es un juicio sustantivo. Un registro que solo guarda que hubo
consentimiento de un adulto no documenta el elemento del que depende su propia
legalidad. La regla vigente del dominio —no divulgar un NNA a la familia por sola causal
de interés vital, exigiendo representante legal o autoridad— va en la dirección correcta y
es más estricta que el texto legal; lo que falta es que el asiento de auditoría conserve
la motivación de interés superior, no únicamente la identidad de quien autorizó.

## 9. Ya existe un registro nacional de personas desaparecidas, y este servicio no es ese

El artículo 9 de la Ley 589 de 2000 creó el Registro Nacional de Desaparecidos,
reglamentado por el Decreto 4218 de 2005 y coordinado por el Instituto Nacional de
Medicina Legal y Ciencias Forenses; su plataforma es el SIRDEC. La Ley 1408 de 2010 lo
confirma y ordena su actualización permanente: su artículo 3 exige transferir al Instituto
la información necesaria para actualizar el Registro "conforme a los requisitos y fuentes
establecidas en la Ley 589 de 2000, en el Decreto 4218 de 2005 y en el Plan Nacional de
Búsqueda", y encarga ajustar el Formato Único de Personas Desaparecidas y el SIRDEC
[H10][H11].

Ese régimen está construido alrededor del delito de desaparición forzada y de la
identificación forense, no de la respuesta a desastres, de modo que no gobierna
directamente a `found_persons`. La consecuencia es de vocabulario y de alcance, y encaja
con la regla de oro del [glosario](../glossary.md): este servicio no es el Registro
Nacional de Desaparecidos, no lo reemplaza y no debe presentarse ante una familia ni ante
una autoridad como si tuviera su valor. Queda abierta una pregunta que las fuentes
consultadas no resuelven y que merece opinión legal propia: si el registro de una persona
localizada genera algún deber de reporte cuando esa persona figuraba previamente como
desaparecida.

## 10. Correcciones a la documentación vigente

Revisando las citas de `HABEAS-DATA.md` contra el texto de las normas aparecieron dos
errores, ambos ya corregidos en ese archivo:

1. **Artículo equivocado en el límite a la supresión.** El documento atribuía a
   `Decreto 1074 art. 2.2.2.25.2.5` la exclusión de la supresión. Ese artículo compila el
   artículo 8 del Decreto 1377 de 2013, que trata de la *prueba de la autorización*. El
   límite a la supresión está en el artículo 9 del Decreto 1377, compilado como
   `2.2.2.25.2.6` [H4][H5].
2. **Redacción equivocada del límite.** No es que la supresión se excluya cuando
   "obstruye una actuación judicial o administrativa". El texto dice: "La solicitud de
   supresión de la información y la revocatoria de la autorización no procederán cuando el
   Titular tenga un deber legal o contractual de permanecer en la base de datos" [H4].
   La diferencia tiene efecto en el código: `Retention.legal_hold` no cumple el estándar
   con un motivo en texto libre, porque lo que la norma exige identificar es **el deber
   legal o contractual** que obliga a conservar. Ese deber es lo que debe quedar nombrado
   en el campo y lo que se le responde al Titular en el 409.

Se confirma también, por si sirve para cerrar el pendiente de plazos, que los días
festivos que el cálculo actual no contempla están fijados en la Ley 51 de 1983, que además
traslada varios de ellos al lunes siguiente cuando no caen en lunes [H12] — el calendario
no es una lista fija por fecha y hay que generarlo por año.

## 11. Lo que las fuentes consultadas no resuelven

> [!IMPORTANT]
> La lectura del artículo 6 lit. b) que sostiene a este servicio se apoya en derecho
> comparado y en doctrina humanitaria, **no en jurisprudencia colombiana aplicada a un
> desastre**. No se encontró ninguna sentencia ni doctrina publicada de la SIC que
> resuelva si un sismo activa la causal de interés vital, ni que precise qué prueba de
> incapacidad se exige. C-748 de 2011 es control abstracto de la ley, no un caso
> concreto. Tratar esta fundamentación como una base razonada y defendible, no como
> certeza jurídica establecida.

Además quedan abiertos: si el ámbito `responder` puede ver la categoría Salud sin ser
personal sanitario o delegado (sección 6); si existe deber de reporte al Registro Nacional
de Desaparecidos (sección 9); y qué constancia concreta de interés superior debe exigirse
en la ruta NNA (sección 8). Ninguno se resuelve con las fuentes de la tabla siguiente;
los tres necesitan concepto de abogado.

## Referencias

| ID | Fuente | URL |
|---|---|---|
| H1 | Constitución Política de Colombia, art. 15 (intimidad y habeas data) | https://www.mincit.gov.co/ministerio/normograma-sig/procesos-estrategicos/gestion-de-informacion-y-comunicacion/constitucion-politica/derechos/articulo-15.aspx |
| H2 | Ley 1581 de 2012, arts. 4, 6, 7, 8, 10, 12, 25 — texto completo | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=49981 |
| H3 | Corte Constitucional, Sentencia C-748 de 2011 (control previo de la ley estatutaria; exequibilidad condicionada del art. 7) | https://www.corteconstitucional.gov.co/relatoria/2011/c-748-11.htm |
| H4 | Decreto 1377 de 2013, arts. 8 y 9 (compilación jurídica MINTIC, con la correspondencia a la numeración del Decreto 1074) | https://normograma.mintic.gov.co/mintic/compilacion/docs/decreto_1377_2013.htm |
| H5 | Decreto 1074 de 2015 — Decreto Único Reglamentario del Sector Comercio, Industria y Turismo (protección de datos: Libro 2, Parte 2, Título 2, Cap. 25) | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=62508 |
| H6 | Reglamento (UE) 2016/679 (RGPD), art. 9(2)(c) y Considerando 46 | https://gdpr-info.eu/art-9-gdpr/ · https://gdpr-info.eu/recitals/no-46/ |
| H7 | Marelli, M. (ed.) (2024). *Handbook on Data Protection in Humanitarian Action*, 3ª ed. Cambridge University Press / CICR. Acceso abierto CC-BY-NC-ND. Secciones 3.1 y 3.3 (interés vital), cap. 7 (drones y búsqueda), cap. sobre biometría, glosario (*Sought Person*). ISBN 978-1-009-41462-3 | https://doi.org/10.1017/9781009414630 |
| H8 | 33ª Conferencia Internacional de la Cruz Roja y de la Media Luna Roja (Ginebra, 9–12 dic. 2019). Resolución 33IC/19/R4, *Restoring Family Links while respecting privacy, including as it relates to personal data protection*, párrs. 11 y 12 | https://rcrcconference.org/app/uploads/2019/12/33IC-R4-RFL-_CLEAN_ADOPTED_en.pdf |
| H9 | Ley 1523 de 2012 — política nacional de gestión del riesgo de desastres y SNGRD (arts. 13, 14, 27, 45, 46) | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=47141 |
| H10 | Ley 589 de 2000, art. 9 — creación del Registro Nacional de Desaparecidos (reglamentado por el Decreto 4218 de 2005) | Ver nota de verificación |
| H11 | Ley 1408 de 2010, art. 3 y ss. — actualización del Registro Nacional de Desaparecidos y del SIRDEC | https://www.unidadvictimas.gov.co/sites/default/files/documentosbiblioteca/ley-1408-de-2010.pdf |
| H12 | Ley 51 de 1983 — descanso remunerado en días festivos y traslado al lunes | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=4954 |
| H13 | Muñoz del-Carpio-Toia, A. et al. (2023). "Protección de datos de salud: el reto de la armonización legislativa en América Latina." *Rev. Cuerpo Médico HNAAA* (fuente secundaria académica, contexto regional del art. 6) | https://pmc.ncbi.nlm.nih.gov/articles/PMC11349313/ |

### Nota de verificación

Verificado el 23 de agosto de 2026. Cada cita textual de este documento se tomó de la
fuente recuperada, no de memoria. Precisiones sobre el alcance de esa verificación:

- **H7** se descargó completo desde Cambridge Core y se leyó directamente; las comillas de
  las secciones 4, 5 y 6 son transcripción literal de ese PDF. La edición vigente es la
  **tercera (2024)**, no la segunda de 2020 que aparece con más frecuencia en búsquedas.
- **H8** se descargó y se leyó; el párrafo 11 está transcrito literal.
- **H11** se descargó y se leyó; el artículo 3 está transcrito literal.
- **H10 no se pudo recuperar directamente.** `funcionpublica.gov.co` y
  `secretariasenado.gov.co` —las fuentes canónicas de texto legal colombiano— fallan por
  error de certificado TLS, igual que en la verificación anterior de este proyecto. La
  existencia y el contenido del artículo 9 de la Ley 589 de 2000 se confirmaron de forma
  indirecta pero sólida: la Ley 1408 de 2010 (H11, leída en su texto) lo cita
  expresamente como fuente del Registro Nacional de Desaparecidos junto con el Decreto
  4218 de 2005. Si se va a citar el texto exacto del artículo 9 en material externo,
  confirmarlo antes en una fuente oficial recuperable.
- **H5**, por el tamaño del Decreto Único, se verificó en cuanto a autenticidad del
  documento y a la correspondencia de numeración a través de H4, que es la compilación
  oficial del decreto reglamentario original.
- Se intentó incorporar guía de autoridades de control europeas sobre la interpretación
  restrictiva del interés vital (ICO del Reino Unido y AEPD de España). Ambas devolvieron
  error de servidor (403 y 500) y **no se citan**, en vez de citarlas sin haberlas leído.
