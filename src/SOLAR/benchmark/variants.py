from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VariantSpec:
    """One named SOLAR or objective-control configuration."""

    name: str
    group: str
    objective: str
    evidence_scope: str
    description: str
    model_kwargs: dict[str, Any]

    def resolved_model_kwargs(self, anchor_seed: int = 0) -> dict[str, Any]:
        kwargs = copy.deepcopy(self.model_kwargs)
        if self.objective == "solar_supcon":
            kwargs["anchor_seed"] = int(anchor_seed)
        return kwargs


def _solar(
    name: str,
    group: str,
    evidence_scope: str,
    description: str,
    **model_kwargs: Any,
) -> VariantSpec:
    return VariantSpec(
        name=name,
        group=group,
        objective="solar_supcon",
        evidence_scope=evidence_scope,
        description=description,
        model_kwargs=model_kwargs,
    )


_SPECS = [
    _solar('solar_orthogonal_uniq', 'matched_controls', '450_fit_campaign',
           'Orthogonal anchors included once per present label in the contrastive pool.',
           semantic_mode='onehot', anchor_geometry='orthogonal', anchor_dedup=True,
           imbalance_mode='natural'),
    _solar('solar_orthogonal', 'reviewer_main', 'reviewer_fairness_and_lobo_matrix', 'Controlled orthogonal anchors at the configured embedding dimension (reviewer main).', semantic_mode='onehot', anchor_geometry='orthogonal', anchor_dedup=False, imbalance_mode='natural'),
    _solar('solar_none', 'reviewer_main', 'reviewer_fairness_and_lobo_matrix', 'Expression-only supervised contrastive learning without an anchor branch.', semantic_mode='none', embedding_dim=128, anchor_dedup=False, imbalance_mode='natural'),
    _solar('solar_trainable', 'reviewer_mechanism', 'reviewer_mechanism_333_job_matrix', 'Trainable 128-dimensional class anchors.', semantic_mode='trainable', embedding_dim=128, anchor_dedup=False, imbalance_mode='natural'),
    _solar('solar_geometry_gaussian', 'reviewer_mechanism', 'reviewer_mechanism_333_job_matrix', 'Controlled 128-dimensional gaussian anchor geometry.', semantic_mode='onehot', embedding_dim=128, anchor_geometry='gaussian', anchor_coherence=None, anchor_dedup=False, imbalance_mode='natural'),
]

VARIANTS = {spec.name: spec for spec in _SPECS}


def get_variant(name: str) -> VariantSpec:
    try:
        return VARIANTS[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown SOLAR benchmark variant {name!r}. "
            f"Available: {', '.join(sorted(VARIANTS))}"
        ) from exc


def list_variants(group: str | None = None) -> list[VariantSpec]:
    variants = VARIANTS.values()
    if group is not None:
        variants = (spec for spec in variants if spec.group == group)
    return sorted(variants, key=lambda spec: (spec.group, spec.name))
