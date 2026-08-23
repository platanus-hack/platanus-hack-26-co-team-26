# ADR-0010: API de personas localizadas bajo régimen de habeas data

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Miguel (API). **Revisores:** Helmut (firma y sellado), Laura (NNA y vocabulario).

**Fundamentación jurídica y referencias:** [HABEAS-DATA-FUNDAMENTACION-JURIDICA.md](../../privacy/HABEAS-DATA-FUNDAMENTACION-JURIDICA.md)

## Contexto

Falta la contraparte de todo el sistema: HELIUS mueve señales de que alguien
podría estar en algún sitio, pero no tenía dónde anotar el desenlace — que esa
persona **apareció**. Sin eso, las familias siguen preguntando y los organismos de
socorro siguen buscando a gente que ya está en un albergue.

El dato es especialmente delicado. Un registro de personas localizadas es, mirado
con malicia, un directorio de damnificados con su ubicación actual: exactamente lo
que sirve para saqueo dirigido, fraude, acoso o suplantación. Y el escenario de uso
—alguien atrapado o inconsciente— es justamente aquel en que no hay autorización
que recoger.

En Colombia esto no es una cuestión de buenas prácticas sino de derecho positivo:
Constitución art. 15, Ley 1581 de 2012, Decreto 1074 de 2015, con la SIC como
autoridad. Los datos de salud son sensibles (art. 5) y su tratamiento está prohibido
salvo causal tasada (art. 6).

## Decisión

Un hexágono independiente, `services/found_persons`, en el que **el cumplimiento es
una invariante del dominio y no una capa de validación en el borde**.

Cinco decisiones concretas:

1. **No existe registro sin base legal.** `Consent` es un campo obligatorio de
   `FoundPersonRecord`, y `validate()` rechaza el registro si contiene datos
   sensibles bajo una causal que el art. 6 no habilita. Las categorías se **calculan
   del contenido**, no se declaran: si alguien ubica a la persona en un centro
   asistencial, el registro pasa a tener categoría de salud aunque el formulario no
   lo dijera. Si dependiera de marcar una casilla, bastaría con no marcarla.

2. **Una sola puerta de salida.** `policies.decide()` y `policies.project()` son el
   único camino por el que un dato abandona el proceso — lo usan por igual el `GET`
   de detalle, el listado y la cápsula de malla. No puede haber un endpoint olvidado
   con reglas más laxas.

3. **Búsqueda solo por token ciego.** `HMAC-SHA256(clave_del_incidente, documento)`.
   Un dispositivo solo puede preguntar por alguien cuyo documento ya conoce; no hay
   búsqueda por nombre en ninguna ruta. La clave es por incidente, de modo que el
   token no correlaciona a la misma persona entre desastres.

4. **Sin oráculo de existencia en los ámbitos bajos.** Para `public` y `family`, "no
   existe" y "existe pero no te corresponde" devuelven la misma respuesta. Se
   sacrifica claridad operativa para que la API no permita comprobar, con un
   documento ajeno, si esa persona está registrada.

5. **La supresión alcanza a la malla.** `DELETE` redacta la PII y emite una lápida
   firmada; los dispositivos la sincronizan de forma incremental y borran sus copias.
   Sin este canal, borrar en el servidor sería una ficción para todo teléfono que ya
   tuviera el dato.

## Alternativas consideradas

**Añadir los endpoints a `services/shared`.** Descartada: `shared` es el kernel común
y este dominio tiene reglas que no aplican a nadie más. Meterlas ahí las convertiría
en carga para los otros cinco servicios.

**Autorización previa siempre, sin excepciones.** Descartada por inaplicable: el caso
central es una persona que no puede autorizar nada. La ley previó esto en el art. 6
lit. b y en el art. 10 lit. c; lo que hacemos es exigir que la excepción sea
explícita, justificada por escrito y **caducable**.

**Devolver 404 cuando el ámbito no alcanza.** Descartada: distinguir 404 de 403
convierte la ruta en un oráculo. Ver decisión 4.

**Borrado físico en `DELETE`.** Descartada: el `audit_log` tiene que seguir apuntando
a algo —el Titular tiene derecho a saber quién vio su dato antes de que se borrara— y
el conteo agregado del incidente no puede cambiar retroactivamente. Se redacta la PII
y sobrevive un esqueleto que no identifica a nadie.

**Justificación y finalidad como parámetros de consulta.** Descartada: una
justificación real es PII y en la URL acabaría replicada en el log de acceso de cada
proxy, contra la Definition of Done ("sin PII en logs"). Van en cabecera, con
percent-encoding porque HTTP no transporta UTF-8.

## Consecuencias

**Se gana:** un servicio defendible ante la SIC; trazabilidad real que el Titular
puede leer; y un mecanismo de supresión que funciona fuera del servidor, que era el
problema abierto de cualquier arquitectura con réplicas en teléfonos.

**Se sacrifica:** ergonomía. Toda petición necesita finalidad y justificación; no hay
búsqueda por nombre; el ámbito familiar recibe menos de lo que le gustaría. Cada una
de esas fricciones es una decisión, no un descuido.

**Deuda asumida:** persistencia en SQLite en vez de PostgreSQL+PostGIS (detrás del
puerto `RecordRepository`); `DEV_TOKENS` en lugar del IdP del incidente; plazos en
días hábiles sin calendario de festivos, lo que los acorta respecto del término legal
— el lado seguro por el que equivocarse, pero inexacto.

**Se revisa** cuando exista el IdP del incidente, o al primer despliegue real con
datos de personas, lo que ocurra antes. Un cambio en `SCOPE_CEILING` o en la lista de
`LegalBasis` exige ADR nuevo.
