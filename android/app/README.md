# :android:app

**Propósito:** app Android (Compose, navegación, DI, `EmergencyForegroundService`).
UI en `ui/{ready,prepare,emergency,rescuer,aib,design}` — ver
`docs/architecture/OVERVIEW.md` § 13 y el requisito de diseño duro de la UI del
atrapado (botones gigantes, tema oscuro puro, sin navegación profunda).

**Puertos que expone:** ninguno (es el *driving adapter* principal — consume los
casos de uso de `:core` vía Compose).

**Dueño:** Laura + Jorge (diseño y desarrollo conjunto de la app móvil).

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).
