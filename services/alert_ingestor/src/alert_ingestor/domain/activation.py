"""Decisión de activación (Sección 12.4 del spec): ¿este incidente enciende el
resto del sistema (notificaciones, cambio de modo de energía en el móvil, etc.)?

Dos caminos para activar: una magnitud alta reportada por una sola fuente ya
alcanza, o una magnitud menor pero **corroborada** por varias fuentes
independientes — porque una coincidencia entre redes que no comparten estaciones
ni algoritmo es en sí misma una señal de confianza, incluso con una magnitud que
aisladamente no bastaría.

Dueño: Miguel.
"""

from __future__ import annotations

from alert_ingestor.domain.models import ActivationDecision, ActivationPolicy, SeismicIncident


def decide_activation(
    incident: SeismicIncident, policy: ActivationPolicy | None = None
) -> ActivationDecision:
    policy = policy or ActivationPolicy()
    magnitude = incident.magnitude

    if magnitude >= policy.min_magnitude_single_source:
        return ActivationDecision(
            incident=incident,
            should_activate=True,
            reason=(
                f"Magnitud {magnitude:.1f} ≥ {policy.min_magnitude_single_source} "
                "(umbral de activación por magnitud, ASSUMED)."
            ),
            policy=policy,
        )

    if (
        incident.source_count >= policy.min_corroborating_sources
        and magnitude >= policy.min_magnitude_corroborated
    ):
        return ActivationDecision(
            incident=incident,
            should_activate=True,
            reason=(
                f"Magnitud {magnitude:.1f} ≥ {policy.min_magnitude_corroborated} "
                f"corroborada por {incident.source_count} fuentes independientes "
                f"({', '.join(sorted(s.value for s in incident.sources))})."
            ),
            policy=policy,
        )

    return ActivationDecision(
        incident=incident,
        should_activate=False,
        reason=(
            f"Magnitud {magnitude:.1f} con {incident.source_count} fuente(s): no "
            "alcanza ni el umbral individual ni el corroborado (ambos ASSUMED, "
            "ver docs/validation/)."
        ),
        policy=policy,
    )
