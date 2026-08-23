# Vocabulario del proyecto

Este glosario es normativo: el linter de CI (`arch-guard.yml`,
`.pre-commit-config.yaml`) bloquea PRs que usen la columna prohibida en código, UI,
documentación o material comercial.

## Regla de oro

> No prometemos encontrar a nadie. Prometemos que la información que puede ayudar
> a encontrarte no desaparezca cuando desaparece tu infraestructura.

## Usar / Nunca usar

| Usar | Nunca usar | Por qué |
|---|---|---|
| Análisis e Interpretación de Biomarcadores (AIB) | triage, diagnóstico, signos vitales médicos | El módulo estima, no diagnostica. |
| Evidencia de actividad | detector de vida | No detecta "vida"; detecta movimiento/patrón. |
| Estimación de pulso con SQI | frecuencia cardíaca medida | Toda cifra lleva un índice de calidad, nunca se presenta como medición clínica exacta. |
| Zona candidata con confianza | ubicación exacta | La localización es probabilística (68%/95%), nunca un punto certero. |
| `NO_RECENT_EVIDENCE`, `UNCONFIRMED` | muerto, fallecido, herido | El sistema nunca declara el estado vital de nadie — ver `ResponseState`, que no tiene esos valores. |
| Alerta temprana / activación de evento | predicción de sismos | No predecimos terremotos; reaccionamos a una fuente sísmica ya detectada. |
| Proxy experimental de SpO2 (modo investigación) | oximetría | Una cámara RGB no es un oxímetro calibrado — ver estado del arte en el `README.md` raíz. |
| Disponible en Android. iOS en desarrollo. | multiplataforma | Mientras iOS esté en standby (ADR-0002), la comunicación pública no debe sugerir soporte que no existe. |

## Restricciones no negociables (resumen; ver `README.md` raíz para el detalle)

1. No predecimos terremotos.
2. No hacemos triage médico — el módulo se llama AIB.
3. No medimos SpO2 con validez clínica desde la cámara.
4. No detectamos hemorragias, adrenalina ni gravedad de heridas.
5. No convertimos a un teléfono sin la app en un nodo de la malla.
6. No declaramos a nadie fallecido. El estado `DEAD`/`ALIVE`/`INJURED` no existe en ningún enum.
7. RSSI no es distancia — toda conversión directa RSSI→metros sin modelo probabilístico se rechaza en code review.
8. No prometemos cobertura iOS mientras esté en standby.

**Dueño de este documento:** Laura (vocabulario clínico/claims). **Revisor:** Alex.
