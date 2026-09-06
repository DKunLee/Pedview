from __future__ import annotations

from functools import cache

from .layout import assign_generations
from .models import Family


def compute_family_relatedness(
    family: Family,
    ancestor_inbreeding: float = 0.0,
) -> dict[str, dict[str, float]]:
    family.ensure_relationships()
    generations = assign_generations(family)
    parent_map = {
        person_id: (
            person.father_id if person.father_id in family.members else None,
            person.mother_id if person.mother_id in family.members else None,
        )
        for person_id, person in family.members.items()
    }

    @cache
    def kinship(left_id: str | None, right_id: str | None) -> float:
        if left_id is None or right_id is None:
            return 0.0
        if left_id == right_id:
            father_id, mother_id = parent_map[left_id]
            if father_id is None and mother_id is None:
                return 0.5 * (1.0 + ancestor_inbreeding)
            return 0.5 * (1.0 + kinship(father_id, mother_id))

        if generations[left_id] < generations[right_id] or (
            generations[left_id] == generations[right_id] and left_id > right_id
        ):
            left_id, right_id = right_id, left_id

        father_id, mother_id = parent_map[left_id]
        if father_id is None and mother_id is None:
            return 0.0
        return 0.5 * (kinship(father_id, right_id) + kinship(mother_id, right_id))

    relatedness: dict[str, dict[str, float]] = {}
    for left_id in family.order:
        values: dict[str, float] = {}
        for right_id in family.order:
            coefficient = 2.0 * kinship(left_id, right_id)
            if left_id == right_id or coefficient > 0:
                values[right_id] = coefficient
        relatedness[left_id] = values

    return relatedness
