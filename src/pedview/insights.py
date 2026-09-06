from __future__ import annotations

from functools import cache

from .layout import assign_generations
from .models import Family
from .phenotypes import affected_status_from_metadata
from .segregation import analyze_family_segregation


def build_family_insights(
    family: Family, variant_name: str | None = None
) -> dict[str, object]:
    family.ensure_relationships()
    generations = assign_generations(family)
    order_index = family.order_index()
    people = family.members
    person_ids = list(family.order)
    founder_ids = [
        person_id
        for person_id, person in people.items()
        if person.father_id not in people and person.mother_id not in people
    ]
    founder_id_set = set(founder_ids)
    affected_status = {
        person_id: affected_status_from_metadata(person.metadata)
        for person_id, person in people.items()
    }
    parent_map = {
        person_id: (
            person.father_id if person.father_id in people else None,
            person.mother_id if person.mother_id in people else None,
        )
        for person_id, person in people.items()
    }
    children_by_parent = {person_id: [] for person_id in person_ids}
    partners_by_person = {person_id: set() for person_id in person_ids}
    for relationship in family.relationships:
        if relationship.father_id in people and relationship.mother_id in people:
            partners_by_person[relationship.father_id].add(relationship.mother_id)
            partners_by_person[relationship.mother_id].add(relationship.father_id)
        for parent_id in relationship.parent_ids:
            if parent_id in people:
                children_by_parent[parent_id].extend(relationship.child_ids)

    for parent_id, child_ids in children_by_parent.items():
        children_by_parent[parent_id] = sorted(
            set(child_ids),
            key=lambda child_id: order_index.get(child_id, 0),
        )

    @cache
    def descendants(person_id: str) -> tuple[str, ...]:
        found: set[str] = set()
        for child_id in children_by_parent.get(person_id, ()):
            if child_id in found:
                continue
            found.add(child_id)
            found.update(descendants(child_id))
        return tuple(sorted(found, key=lambda child_id: order_index.get(child_id, 0)))

    def summarize_people(
        target_ids: list[str] | tuple[str, ...] | set[str],
    ) -> dict[str, int]:
        ids = list(target_ids)
        return {
            "total": len(ids),
            "affected": sum(
                affected_status.get(person_id) == "affected" for person_id in ids
            ),
            "unaffected": sum(
                affected_status.get(person_id) == "unaffected" for person_id in ids
            ),
            "unknown_status": sum(
                affected_status.get(person_id) == "unknown" for person_id in ids
            ),
            "male": sum(people[person_id].sex == "male" for person_id in ids),
            "female": sum(people[person_id].sex == "female" for person_id in ids),
            "unknown_sex": sum(
                people[person_id].sex not in {"male", "female"} for person_id in ids
            ),
        }

    generation_stats: list[dict[str, int]] = []
    for generation in sorted(set(generations.values())):
        ids = [
            person_id
            for person_id in person_ids
            if generations.get(person_id) == generation
        ]
        stats = summarize_people(ids)
        stats["generation"] = generation
        generation_stats.append(stats)

    founder_stats = summarize_people(founder_ids)

    def sibling_ids_for(person_id: str) -> list[str]:
        father_id, mother_id = parent_map[person_id]
        sibling_ids: set[str] = set()
        for parent_id in (father_id, mother_id):
            if parent_id is None:
                continue
            sibling_ids.update(children_by_parent.get(parent_id, ()))
        sibling_ids.discard(person_id)
        return sorted(
            sibling_ids, key=lambda sibling_id: order_index.get(sibling_id, 0)
        )

    person_summaries: dict[str, dict[str, object]] = {}
    family_flags: list[dict[str, object]] = []
    flags_by_person = {person_id: [] for person_id in person_ids}

    def add_flag(
        *,
        code: str,
        severity: str,
        message: str,
        person_id: str,
        related_ids: list[str] | None = None,
    ) -> None:
        flag = {
            "code": code,
            "severity": severity,
            "message": message,
            "person_id": person_id,
            "related_ids": related_ids or [],
        }
        flags_by_person[person_id].append(flag)
        family_flags.append(flag)

    for person_id in person_ids:
        father_id, mother_id = parent_map[person_id]
        parent_ids = [parent_id for parent_id in (father_id, mother_id) if parent_id]
        sibling_ids = sibling_ids_for(person_id)
        child_ids = children_by_parent.get(person_id, [])
        descendant_ids = list(descendants(person_id))
        partner_ids = sorted(
            partners_by_person.get(person_id, set()),
            key=lambda partner_id: order_index.get(partner_id, 0),
        )
        first_degree_ids = sorted(
            set(parent_ids) | set(sibling_ids) | set(child_ids),
            key=lambda relative_id: order_index.get(relative_id, 0),
        )

        person_summaries[person_id] = {
            "partners": partner_ids,
            "parents": {
                "ids": parent_ids,
                **summarize_people(parent_ids),
            },
            "siblings": {
                "ids": sibling_ids,
                **summarize_people(sibling_ids),
            },
            "children": {
                "ids": child_ids,
                **summarize_people(child_ids),
            },
            "descendants": {
                "ids": descendant_ids,
                **summarize_people(descendant_ids),
            },
            "first_degree": {
                "ids": first_degree_ids,
                **summarize_people(first_degree_ids),
            },
        }

        person_status = affected_status.get(person_id)
        explicit_parent_statuses = [
            affected_status[parent_id]
            for parent_id in parent_ids
            if affected_status.get(parent_id) in {"affected", "unaffected"}
        ]
        if (
            person_status == "affected"
            and len(parent_ids) == 2
            and explicit_parent_statuses == ["unaffected", "unaffected"]
        ):
            add_flag(
                code="affected_with_unaffected_parents",
                severity="warning",
                message="Affected individual has two recorded unaffected parents.",
                person_id=person_id,
                related_ids=parent_ids,
            )
        if (
            person_status == "unaffected"
            and len(parent_ids) == 2
            and explicit_parent_statuses == ["affected", "affected"]
        ):
            add_flag(
                code="unaffected_with_affected_parents",
                severity="warning",
                message="Unaffected individual has two recorded affected parents.",
                person_id=person_id,
                related_ids=parent_ids,
            )
        if (
            person_status == "affected"
            and parent_ids
            and not any(
                affected_status.get(relative_id) == "affected"
                for relative_id in first_degree_ids
            )
        ):
            add_flag(
                code="isolated_affected_case",
                severity="notice",
                message="Affected individual has no affected first-degree relatives recorded.",
                person_id=person_id,
            )

    branch_summaries: list[dict[str, object]] = []
    for relationship in family.relationships:
        if relationship.parent_ids and not all(
            parent_id in founder_id_set for parent_id in relationship.parent_ids
        ):
            continue
        branch_member_ids = set(relationship.parent_ids)
        branch_descendant_ids: set[str] = set()
        for child_id in relationship.child_ids:
            branch_descendant_ids.add(child_id)
            branch_descendant_ids.update(descendants(child_id))
        branch_member_ids.update(branch_descendant_ids)
        member_ids = sorted(
            branch_member_ids, key=lambda person_id: order_index.get(person_id, 0)
        )
        descendant_ids = sorted(
            branch_descendant_ids,
            key=lambda person_id: order_index.get(person_id, 0),
        )
        label = (
            " + ".join(relationship.parent_ids)
            if relationship.parent_ids
            else relationship.relationship_id
        )
        branch_summaries.append(
            {
                "label": label,
                "root_ids": list(relationship.parent_ids),
                "member_count": len(member_ids),
                "descendant_count": len(descendant_ids),
                "affected_count": sum(
                    affected_status.get(member_id) == "affected"
                    for member_id in member_ids
                ),
                "affected_descendant_count": sum(
                    affected_status.get(descendant_id) == "affected"
                    for descendant_id in descendant_ids
                ),
            }
        )

    branch_summaries.sort(
        key=lambda item: (
            -int(item["affected_descendant_count"]),
            -int(item["descendant_count"]),
            str(item["label"]),
        )
    )

    segregation = analyze_family_segregation(family, variant_name=variant_name)
    if segregation:
        for err in segregation.get("mendelian_errors", []):
            flag = {
                "severity": "warning",
                "person_id": err["person_id"],
                "message": f"Mendelian Inconsistency: {err['message']}",
            }
            family_flags.append(flag)
            flags_by_person[err["person_id"]].append(flag)
        for dn_id in segregation.get("de_novo_ids", []):
            flag = {
                "severity": "notice",
                "person_id": dn_id,
                "message": "Candidate De Novo variant: mutation observed in child but neither biological parent.",
            }
            family_flags.append(flag)
            flags_by_person[dn_id].append(flag)

    family_flags.sort(
        key=lambda flag: (
            {"warning": 0, "notice": 1}.get(str(flag["severity"]), 2),
            order_index.get(str(flag["person_id"]), 0),
            str(flag["message"]),
        )
    )

    for person_id in person_ids:
        person_summaries[person_id]["flags"] = flags_by_person[person_id]

    return {
        "generation_stats": generation_stats,
        "founder_stats": founder_stats,
        "branch_summaries": branch_summaries,
        "family_flags": family_flags,
        "person_summaries": person_summaries,
        "segregation": segregation,
    }
